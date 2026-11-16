#pragma once
#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace pr {
using Vertex = std::uint32_t;
using Edge = std::pair<Vertex, Vertex>; // source, destination
struct Graph {
    std::vector<std::uint64_t> offsets; // incoming CSR
    std::vector<Vertex> sources;
    std::vector<std::uint64_t> outdegree;
    std::vector<double> inverse_outdegree;
    std::size_t vertices() const { return outdegree.size(); }
    std::size_t edges() const { return sources.size(); }
    static Graph from_edges(std::size_t n, const std::vector<Edge>& edges);
};
struct LoadOptions {
    std::string format = "auto"; // auto, edgelist, mtx
    int index_base = 0; // edge lists only; Matrix Market is always one-based
    std::size_t vertices = 0; // edge lists: 0 means infer from largest ID
};
Graph load_graph(const std::string& path, const LoadOptions& options = {});
enum class Strategy { serial, static_schedule, dynamic, guided, edge_balanced };
Strategy parse_strategy(const std::string& name);
std::string strategy_name(Strategy strategy);
struct Options {
    Strategy strategy = Strategy::serial;
    int threads = 1;
    int chunk = 0; // 0: static block default; dynamic/guided default 1
    int max_iterations = 100;
    double tolerance = 1e-10; // absolute L1 iterate difference; 0 = fixed iterations
    double damping = 0.85;
    bool profile = false;
};
struct alignas(64) ThreadStats {
    std::uint64_t rows = 0, edges = 0;
    double update_seconds = 0;
};
struct Result {
    std::vector<double> ranks;
    int iterations = 0, actual_threads = 1;
    bool converged = false;
    double residual = 0, rank_sum = 0;
    double kernel_seconds = 0, setup_seconds = 0, total_seconds = 0;
    double partition_seconds = 0;
    std::vector<std::size_t> partitions;
    std::vector<ThreadStats> thread_stats;
};
// O(p log n), using incoming CSR offsets as the existing edge prefix sums.
std::vector<std::size_t> edge_partitions(const Graph& graph, int threads);
Result pagerank(const Graph& graph, const Options& options = {});
} // namespace pr
