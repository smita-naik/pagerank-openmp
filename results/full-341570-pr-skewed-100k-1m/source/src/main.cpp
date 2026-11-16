#include "pagerank.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <omp.h>

#ifndef PR_BUILD_FLAGS
#define PR_BUILD_FLAGS "unknown"
#endif
namespace {
std::string quote(const std::string& s) {
    std::ostringstream out;
    out << '"';
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') out << '\\' << c;
        else if (c < 32) out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << static_cast<int>(c);
        else out << c;
    }
    return out.str() + '"';
}
int positive_or_zero(const std::string& s) {
    std::size_t end = 0;
    auto n = std::stoll(s, &end);
    if (end != s.size() || n < 0 || n > 2147483647) throw std::invalid_argument("Invalid integer: " + s);
    return static_cast<int>(n);
}
double real(const std::string& s) {
    std::size_t end = 0;
    auto x = std::stod(s, &end);
    if (end != s.size() || !std::isfinite(x)) throw std::invalid_argument("Invalid number: " + s);
    return x;
}
void help() {
    std::cout << "Usage: pagerank --graph PATH [options]\n"
      "  --strategy serial|static|dynamic|guided|edge-balanced (default serial)\n"
      "  --threads N         Requested team size (default 1)\n"
      "  --chunk N           Scheduling chunk; 0 = runtime default (default 0)\n"
      "  --iterations N      Maximum iterations (default 100)\n"
      "  --tolerance X       Absolute L1 iterate tolerance; 0 = fixed iterations\n"
      "                      (default 1e-10)\n"
      "  --damping X         In [0,1), default 0.85\n"
      "  --format auto|edgelist|mtx\n"
      "  --index-base 0|1    Edge-list IDs only (default 0); mtx is one-based\n"
      "  --vertices N        Include isolated vertices in edge-list graphs\n"
      "  --warmup N          Unreported warmup solves (default 0)\n"
      "  --repeat N          Measured solves (default 1)\n"
      "  --verify            Compare with serial; fail if L1 > 1e-8 or Linf > 1e-9\n"
      "  --profile           Collect per-thread update time/rows/edges\n"
      "  --rank-output PATH  Write final solve's ranks, one per line\n"
      "JSON Lines on stdout; diagnostics on stderr. No graph IO in solve timings.\n";
}
}
int main(int argc, char** argv) {
    try {
        pr::Options options;
        pr::LoadOptions load;
        std::string path, rank_output;
        bool verify = false;
        int warmup = 0, repeat = 1;
        for (int i = 1; i < argc; ++i) {
            std::string key = argv[i];
            if (key == "--help" || key == "-h") { help(); return 0; }
            if (key == "--verify") { verify = true; continue; }
            if (key == "--profile") { options.profile = true; continue; }
            if (i + 1 >= argc) throw std::invalid_argument("Missing value for " + key);
            std::string value = argv[++i];
            if (key == "--graph") path = value;
            else if (key == "--strategy") options.strategy = pr::parse_strategy(value);
            else if (key == "--threads") options.threads = positive_or_zero(value);
            else if (key == "--chunk") options.chunk = positive_or_zero(value);
            else if (key == "--iterations") options.max_iterations = positive_or_zero(value);
            else if (key == "--tolerance") options.tolerance = real(value);
            else if (key == "--damping") options.damping = real(value);
            else if (key == "--format") load.format = value;
            else if (key == "--index-base") load.index_base = positive_or_zero(value);
            else if (key == "--vertices") {
                std::size_t end = 0;
                if (value.empty() || value[0] == '-') throw std::invalid_argument("Invalid vertex count");
                load.vertices = std::stoull(value, &end);
                if (end != value.size() || load.vertices == 0 || load.vertices > UINT32_MAX)
                    throw std::invalid_argument("Invalid vertex count");
            }
            else if (key == "--warmup") warmup = positive_or_zero(value);
            else if (key == "--repeat") repeat = positive_or_zero(value);
            else if (key == "--rank-output") rank_output = value;
            else throw std::invalid_argument("Unknown option: " + key);
        }
        if (path.empty() || repeat == 0) throw std::invalid_argument("--graph is required; --repeat must be positive");
        if (!rank_output.empty() && std::filesystem::exists(rank_output))
            throw std::invalid_argument("Rank output already exists; choose a new path to preserve it");
        if ((options.strategy == pr::Strategy::serial && options.threads != 1) ||
            ((options.strategy == pr::Strategy::serial || options.strategy == pr::Strategy::edge_balanced) && options.chunk != 0))
            throw std::invalid_argument("Serial requires --threads 1; chunk applies only to static/dynamic/guided");
        const auto load_start = std::chrono::steady_clock::now();
        const auto graph = pr::load_graph(path, load);
        const double load_seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - load_start).count();
        std::uint64_t max_in_degree = 0, dangling_vertices = 0, isolated_vertices = 0;
        const double mean_in_degree = static_cast<double>(graph.edges()) / graph.vertices();
        double degree_variance = 0;
        for (std::size_t v = 0; v < graph.vertices(); ++v) {
            auto degree = graph.offsets[v + 1] - graph.offsets[v];
            max_in_degree = std::max(max_in_degree, degree);
            dangling_vertices += graph.outdegree[v] == 0;
            isolated_vertices += graph.outdegree[v] == 0 && degree == 0;
            const double difference = degree - mean_in_degree;
            degree_variance += difference * difference;
        }
        const double indegree_cv = mean_in_degree > 0 ? std::sqrt(degree_variance / graph.vertices()) / mean_in_degree : 0;
        pr::Result reference;
        if (verify) {
            auto serial = options;
            serial.strategy = pr::Strategy::serial;
            serial.threads = 1;
            serial.profile = false;
            reference = pr::pagerank(graph, serial);
        }
        for (int i = 0; i < warmup; ++i) pr::pagerank(graph, options);
        std::cout << std::setprecision(17) << std::boolalpha;
        for (int sample = 0; sample < repeat; ++sample) {
            auto result = pr::pagerank(graph, options);
            double l1 = 0, linf = 0;
            bool finite = std::isfinite(result.rank_sum) && std::isfinite(result.residual);
            for (std::size_t v = 0; v < graph.vertices(); ++v) {
                finite = finite && std::isfinite(result.ranks[v]) && result.ranks[v] >= 0;
                if (verify) {
                    auto error = std::abs(result.ranks[v] - reference.ranks[v]);
                    l1 += error;
                    linf = std::max(linf, error);
                }
            }
            if (!finite || std::abs(result.rank_sum - 1) > 1e-8 || (verify && (l1 > 1e-8 || linf > 1e-9)))
                throw std::runtime_error("Correctness validation failed");
            std::cout << "{\"graph\":" << quote(path)
                << ",\"vertices\":" << graph.vertices() << ",\"edges\":" << graph.edges()
                << ",\"max_in_degree\":" << max_in_degree << ",\"indegree_cv\":" << indegree_cv
                << ",\"dangling_vertices\":" << dangling_vertices << ",\"isolated_vertices\":" << isolated_vertices
                << ",\"strategy\":" << quote(pr::strategy_name(options.strategy))
                << ",\"requested_threads\":" << options.threads << ",\"actual_threads\":" << result.actual_threads
                << ",\"chunk\":" << options.chunk << ",\"sample\":" << sample
                << ",\"max_iterations\":" << options.max_iterations << ",\"tolerance\":" << options.tolerance
                << ",\"damping\":" << options.damping << ",\"iterations\":" << result.iterations
                << ",\"converged\":" << result.converged << ",\"residual_l1\":" << result.residual
                << ",\"rank_sum\":" << result.rank_sum << ",\"kernel_seconds\":" << result.kernel_seconds
                << ",\"setup_seconds\":" << result.setup_seconds << ",\"total_seconds\":" << result.total_seconds
                << ",\"partition_seconds\":" << result.partition_seconds << ",\"load_seconds\":" << load_seconds
                << ",\"profile\":" << options.profile << ",\"verified\":" << verify
                << ",\"verify_l1\":" << l1 << ",\"verify_linf\":" << linf
                << ",\"compiler\":" << quote(__VERSION__) << ",\"build_flags\":" << quote(PR_BUILD_FLAGS)
                << ",\"openmp\":" << _OPENMP << ",\"thread_stats\":[";
            if (options.profile) for (std::size_t t = 0; t < result.thread_stats.size(); ++t) {
                const auto& stats = result.thread_stats[t];
                if (t) std::cout << ',';
                std::cout << "{\"thread\":" << t << ",\"rows\":" << stats.rows << ",\"edges\":" << stats.edges
                    << ",\"update_seconds\":" << stats.update_seconds << '}';
            }
            std::cout << "]}\n";
            if (sample == repeat - 1 && !rank_output.empty()) {
                std::ofstream ranks(rank_output);
                if (!ranks) throw std::runtime_error("Cannot create rank output");
                ranks << std::setprecision(17);
                for (auto value : result.ranks) ranks << value << '\n';
                ranks.close();
                if (!ranks) throw std::runtime_error("Cannot write rank output");
            }
        }
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
