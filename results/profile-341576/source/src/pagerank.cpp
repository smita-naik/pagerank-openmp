#include "pagerank.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <omp.h>

namespace pr {
namespace {
using Clock = std::chrono::steady_clock;
double seconds(Clock::time_point start) { return std::chrono::duration<double>(Clock::now() - start).count(); }
}
Strategy parse_strategy(const std::string& name) {
    if (name == "serial") return Strategy::serial;
    if (name == "static") return Strategy::static_schedule;
    if (name == "dynamic") return Strategy::dynamic;
    if (name == "guided") return Strategy::guided;
    if (name == "edge-balanced") return Strategy::edge_balanced;
    throw std::invalid_argument("Unknown strategy: " + name);
}
std::string strategy_name(Strategy strategy) {
    switch (strategy) {
        case Strategy::serial: return "serial";
        case Strategy::static_schedule: return "static";
        case Strategy::dynamic: return "dynamic";
        case Strategy::guided: return "guided";
        case Strategy::edge_balanced: return "edge-balanced";
    }
    throw std::invalid_argument("Invalid strategy");
}
std::vector<std::size_t> edge_partitions(const Graph& g, int threads) {
    if (threads < 1) throw std::invalid_argument("Threads must be positive");
    std::vector<std::size_t> cuts(static_cast<std::size_t>(threads) + 1, 0);
    cuts.back() = g.vertices();
    const auto m = g.edges();
    for (int t = 1; t < threads; ++t) {
        if (m == 0) {
            cuts[t] = (g.vertices() / threads) * t + (g.vertices() % threads) * t / threads;
        } else {
            // Division before multiplication prevents overflowing m*t.
            auto target = (m / threads) * t + (m % threads) * t / threads;
            cuts[t] = static_cast<std::size_t>(std::lower_bound(g.offsets.begin(), g.offsets.end(), target) - g.offsets.begin());
        }
    }
    return cuts;
}

template<bool Profile>
Result run(const Graph& g, const Options& o) {
    const auto total_start = Clock::now();
    const auto n = g.vertices();
    Result result;
    result.ranks.assign(n, 1.0 / n);
    std::vector<double> next(n), contribution(n);
    result.thread_stats.resize(o.strategy == Strategy::serial ? 1 : o.threads);
    auto update = [&](std::size_t v, double base) {
        double incoming = 0;
        for (auto e = g.offsets[v]; e < g.offsets[v + 1]; ++e) incoming += contribution[g.sources[e]];
        next[v] = base + o.damping * incoming;
        return std::abs(next[v] - result.ranks[v]);
    };
    if (o.strategy == Strategy::serial) {
        const auto kernel_start = Clock::now();
        for (int iteration = 0; iteration < o.max_iterations; ++iteration) {
            double dangling = 0, delta = 0;
            for (std::size_t v = 0; v < n; ++v) {
                contribution[v] = result.ranks[v] * g.inverse_outdegree[v];
                if (!g.outdegree[v]) dangling += result.ranks[v];
            }
            const double base = (1.0 - o.damping + o.damping * dangling) / n;
            Clock::time_point phase_start;
            if constexpr (Profile) phase_start = Clock::now();
            for (std::size_t v = 0; v < n; ++v) delta += update(v, base);
            if constexpr (Profile) {
                result.thread_stats[0].update_seconds += seconds(phase_start);
                result.thread_stats[0].rows += n;
                result.thread_stats[0].edges += g.edges();
            }
            result.ranks.swap(next);
            result.iterations = iteration + 1;
            result.residual = delta;
            result.converged = o.tolerance > 0 && delta <= o.tolerance;
            if (result.converged) break;
        }
        result.kernel_seconds = seconds(kernel_start);
    } else {
        omp_sched_t saved_schedule;
        int saved_chunk;
        omp_get_schedule(&saved_schedule, &saved_chunk);
        const int saved_dynamic = omp_get_dynamic();
        omp_set_dynamic(0);
        auto schedule = omp_sched_static;
        if (o.strategy == Strategy::dynamic) schedule = omp_sched_dynamic;
        if (o.strategy == Strategy::guided) schedule = omp_sched_guided;
        omp_set_schedule(schedule, o.chunk == 0 && schedule != omp_sched_static ? 1 : o.chunk);
        double dangling = 0, delta = 0;
        Clock::time_point kernel_start;
        #pragma omp parallel num_threads(o.threads) shared(dangling, delta, kernel_start, result, next, contribution)
        {
            const int tid = omp_get_thread_num();
            #pragma omp single
            {
                result.actual_threads = omp_get_num_threads();
                if (o.strategy == Strategy::edge_balanced) {
                    auto start = Clock::now();
                    result.partitions = edge_partitions(g, result.actual_threads);
                    result.partition_seconds = seconds(start);
                }
                kernel_start = Clock::now();
            }
            for (int iteration = 0; iteration < o.max_iterations; ++iteration) {
                #pragma omp for schedule(static) reduction(+:dangling)
                for (std::size_t v = 0; v < n; ++v) {
                    contribution[v] = result.ranks[v] * g.inverse_outdegree[v];
                    if (!g.outdegree[v]) dangling += result.ranks[v];
                }
                // The reduction's barrier publishes dangling to every worker.
                // A private base avoids another single-region barrier.
                const double base = (1.0 - o.damping + o.damping * dangling) / n;
                Clock::time_point phase_start;
                if constexpr (Profile) phase_start = Clock::now();
                std::uint64_t rows = 0, edges = 0;
                if (o.strategy == Strategy::edge_balanced) {
                    // One precomputed contiguous range per actual team member.
                    #pragma omp for schedule(static,1) reduction(+:delta) nowait
                    for (int part = 0; part < result.actual_threads; ++part) {
                        for (auto v = result.partitions[part]; v < result.partitions[part + 1]; ++v) {
                            delta += update(v, base);
                            if constexpr (Profile) { ++rows; edges += g.offsets[v + 1] - g.offsets[v]; }
                        }
                    }
                } else {
                    #pragma omp for schedule(runtime) reduction(+:delta) nowait
                    for (std::size_t v = 0; v < n; ++v) {
                        delta += update(v, base);
                        if constexpr (Profile) { ++rows; edges += g.offsets[v + 1] - g.offsets[v]; }
                    }
                }
                if constexpr (Profile) {
                    auto& stats = result.thread_stats[tid];
                    stats.update_seconds += seconds(phase_start);
                    stats.rows += rows;
                    stats.edges += edges;
                }
                // Required: all reductions and next[] writes must finish before swapping.
                #pragma omp barrier
                #pragma omp single
                {
                    result.ranks.swap(next);
                    result.iterations = iteration + 1;
                    result.residual = delta;
                    result.converged = o.tolerance > 0 && delta <= o.tolerance;
                    // Reuse the swap's synchronization to prepare the next iteration.
                    dangling = 0;
                    delta = 0;
                }
                if (result.converged) break;
            }
            #pragma omp single
            { result.kernel_seconds = seconds(kernel_start); }
        }
        omp_set_schedule(saved_schedule, saved_chunk);
        omp_set_dynamic(saved_dynamic);
        result.thread_stats.resize(result.actual_threads);
    }
    result.total_seconds = seconds(total_start);
    result.setup_seconds = result.total_seconds - result.kernel_seconds;
    result.rank_sum = std::accumulate(result.ranks.begin(), result.ranks.end(), 0.0);
    return result;
}
Result pagerank(const Graph& g, const Options& o) {
    if (g.vertices() == 0 || o.threads < 1 || o.chunk < 0 || o.max_iterations < 1 ||
        !std::isfinite(o.tolerance) || o.tolerance < 0 || !std::isfinite(o.damping) ||
        o.damping < 0 || o.damping >= 1)
        throw std::invalid_argument("Invalid PageRank parameters (damping must be in [0,1))");
    return o.profile ? run<true>(g, o) : run<false>(g, o);
}
} // namespace pr
