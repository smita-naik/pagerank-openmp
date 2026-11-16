#include "pagerank.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <numeric>
#include <random>
#include <stdexcept>

namespace {
int checks = 0;
void require(bool value, const std::string& message) {
    ++checks;
    if (!value) throw std::runtime_error(message);
}
// Independent dense transition-matrix oracle. Does not use incoming CSR or its
// contribution buffers. Small graphs only; dangling columns are uniform.
std::vector<double> oracle(std::size_t n, const std::vector<pr::Edge>& edges) {
    std::vector<double> matrix(n * n, 0), degree(n, 0), rank(n, 1.0 / n), next(n);
    for (auto [s, d] : edges) { ++degree[s]; ++matrix[d * n + s]; }
    for (std::size_t s = 0; s < n; ++s)
        for (std::size_t d = 0; d < n; ++d)
            matrix[d * n + s] = degree[s] ? matrix[d * n + s] / degree[s] : 1.0 / n;
    for (int i = 0; i < 10000; ++i) {
        double delta = 0;
        for (std::size_t d = 0; d < n; ++d) {
            next[d] = 0.15 / n;
            for (std::size_t s = 0; s < n; ++s) next[d] += 0.85 * matrix[d * n + s] * rank[s];
            delta += std::abs(next[d] - rank[d]);
        }
        rank.swap(next);
        if (delta < 1e-14) return rank;
    }
    throw std::runtime_error("Dense oracle failed to converge");
}
void compare(const std::vector<double>& a, const std::vector<double>& b, double tolerance = 1e-11) {
    require(a.size() == b.size(), "Rank dimensions differ");
    double error = 0;
    for (std::size_t v = 0; v < a.size(); ++v) {
        require(std::isfinite(a[v]) && a[v] >= 0, "Nonfinite or negative rank");
        error += std::abs(a[v] - b[v]);
    }
    require(error < tolerance, "L1 rank error: " + std::to_string(error));
    require(std::abs(std::accumulate(a.begin(), a.end(), 0.0) - 1) < 1e-12, "Rank mass is not one");
}
void exercise(std::size_t n, const std::vector<pr::Edge>& edges) {
    auto graph = pr::Graph::from_edges(n, edges);
    auto expected = oracle(n, edges);
    pr::Options o;
    o.max_iterations = 1000;
    o.tolerance = 1e-13;
    auto reference = pr::pagerank(graph, o);
    compare(reference.ranks, expected);
    require(reference.converged, "Serial did not converge");
    for (auto name : {"static", "dynamic", "guided", "edge-balanced"}) {
        o.strategy = pr::parse_strategy(name);
        for (int threads : {1, 2, 3, 8}) {
            o.threads = threads;
            for (int chunk : {0, 1, 4}) {
                if (o.strategy == pr::Strategy::edge_balanced && chunk) continue;
                o.chunk = chunk;
                o.profile = true;
                auto result = pr::pagerank(graph, o);
                compare(result.ranks, expected);
                require(result.converged, "Parallel did not converge");
                std::uint64_t rows = 0, traversals = 0;
                for (const auto& stats : result.thread_stats) { rows += stats.rows; traversals += stats.edges; }
                require(rows == n * result.iterations, "Profiling lost/duplicated rows");
                require(traversals == edges.size() * result.iterations, "Profiling lost/duplicated edges");
                require(result.total_seconds >= result.kernel_seconds, "Invalid timing boundaries");
            }
        }
    }
    // Fixed iterations exercise early exit disabled and double-buffer parity.
    for (int iterations : {1, 2, 17}) {
        o = pr::Options{};
        o.max_iterations = iterations;
        o.tolerance = 0;
        reference = pr::pagerank(graph, o);
        for (auto name : {"static", "dynamic", "guided", "edge-balanced"}) {
            o.strategy = pr::parse_strategy(name);
            o.threads = 3;
            auto result = pr::pagerank(graph, o);
            compare(result.ranks, reference.ranks);
            require(result.iterations == iterations && !result.converged, "Fixed iteration mode stopped early");
        }
    }
    for (int threads : {1, 2, 3, 8, 19}) {
        auto cuts = pr::edge_partitions(graph, threads);
        require(cuts.size() == static_cast<std::size_t>(threads + 1), "Wrong partition count");
        require(cuts.front() == 0 && cuts.back() == n, "Partition endpoints wrong");
        require(std::is_sorted(cuts.begin(), cuts.end()), "Partitions not monotonic");
    }
}
}
int main() {
    try {
        exercise(1, {});
        exercise(1, {{0, 0}});
        exercise(7, {}); // every vertex dangling
        exercise(3, {{0, 1}, {1, 2}, {2, 0}}); // uniform cycle
        exercise(4, {{0, 1}, {1, 2}}); // dangling sink and isolated vertex
        exercise(6, {{0, 1}, {1, 0}, {2, 3}, {3, 2}, {4, 4}}); // disconnected
        exercise(4, {{0, 1}, {0, 1}, {1, 1}, {1, 2}, {2, 0}}); // multigraph + self-loop
        std::vector<pr::Edge> hub;
        for (pr::Vertex v = 1; v < 32; ++v) hub.emplace_back(v, 0);
        exercise(32, hub); // indivisible high-indegree row
        std::mt19937 random(548);
        for (int sample = 0; sample < 8; ++sample) {
            std::vector<pr::Edge> edges;
            for (int e = 0; e < 60; ++e) edges.emplace_back(random() % 13, random() % 13);
            exercise(13, edges);
        }
        auto analytic = pr::pagerank(pr::Graph::from_edges(2, {{0, 1}}),
            {pr::Strategy::serial, 1, 0, 1000, 1e-14, 0.85, false});
        compare(analytic.ranks, {1.0 / 2.85, 1.85 / 2.85});
        std::cout << "PASS: " << checks << " checks (dense oracle, analytic, scheduling, partitions, profiling)\n";
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
