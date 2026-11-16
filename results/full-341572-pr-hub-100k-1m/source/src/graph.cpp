#include "pagerank.hpp"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace pr {
namespace {
std::uint64_t integer(const std::string& s) {
    if (s.empty() || s[0] == '-') throw std::runtime_error("Expected nonnegative integer: " + s);
    std::size_t end = 0;
    auto x = std::stoull(s, &end);
    if (end != s.size()) throw std::runtime_error("Invalid integer: " + s);
    return x;
}
bool content(std::ifstream& file, std::string& line) {
    while (std::getline(file, line)) {
        auto start = line.find_first_not_of(" \t\r");
        if (start == std::string::npos || line[start] == '#' || line[start] == '%') continue;
        auto comment = line.find_first_of("#%", start);
        line = line.substr(start, comment == std::string::npos ? comment : comment - start);
        return true;
    }
    return false;
}
Vertex vertex(const std::string& s, int base) {
    auto x = integer(s);
    if (x < static_cast<unsigned>(base) || x - base >= std::numeric_limits<Vertex>::max())
        throw std::runtime_error("Vertex ID outside supported range: " + s);
    return static_cast<Vertex>(x - base);
}
}
Graph Graph::from_edges(std::size_t n, const std::vector<Edge>& edges) {
    if (n == 0 || n > std::numeric_limits<Vertex>::max())
        throw std::invalid_argument("Vertex count must be in [1, UINT32_MAX]");
    Graph g;
    g.offsets.assign(n + 1, 0);
    g.outdegree.assign(n, 0);
    g.inverse_outdegree.resize(n);
    for (auto [source, destination] : edges) {
        if (source >= n || destination >= n) throw std::invalid_argument("Edge endpoint exceeds vertex count");
        ++g.offsets[destination + 1];
        ++g.outdegree[source];
    }
    for (std::size_t v = 0; v < n; ++v) {
        g.offsets[v + 1] += g.offsets[v];
        g.inverse_outdegree[v] = g.outdegree[v] ? 1.0 / g.outdegree[v] : 0.0;
    }
    auto cursor = g.offsets;
    g.sources.resize(edges.size());
    for (auto [source, destination] : edges) g.sources[cursor[destination]++] = source;
    return g;
}
Graph load_graph(const std::string& path, const LoadOptions& options) {
    if (options.index_base != 0 && options.index_base != 1) throw std::invalid_argument("Index base must be 0 or 1");
    std::ifstream file(path);
    if (!file) throw std::runtime_error("Cannot open graph: " + path);
    std::string line;
    std::getline(file, line);
    bool mtx = line.rfind("%%MatrixMarket", 0) == 0;
    if (options.format != "auto" && options.format != "mtx" && options.format != "edgelist")
        throw std::invalid_argument("Format must be auto, mtx, or edgelist");
    if (options.format == "mtx" && !mtx) throw std::runtime_error("Missing Matrix Market banner");
    if (options.format == "edgelist") mtx = false;
    std::vector<Edge> edges;
    std::size_t n = options.vertices;
    if (mtx) {
        std::string banner, object, storage, field, symmetry, extra;
        std::istringstream header(line);
        header >> banner >> object >> storage >> field >> symmetry;
        if (!header || header >> extra || object != "matrix" || storage != "coordinate" ||
            (field != "pattern" && field != "real" && field != "integer") ||
            (symmetry != "general" && symmetry != "symmetric"))
            throw std::runtime_error("Supported Matrix Market: coordinate pattern/real/integer general/symmetric");
        if (!content(file, line)) throw std::runtime_error("Missing Matrix Market dimensions");
        std::string rows, columns, entries;
        std::istringstream dims(line);
        dims >> rows >> columns >> entries;
        if (!dims || dims >> extra) throw std::runtime_error("Invalid Matrix Market dimensions");
        auto r = integer(rows), c = integer(columns), count = integer(entries);
        if (r != c || r == 0 || r > std::numeric_limits<Vertex>::max())
            throw std::runtime_error("PageRank requires a nonempty square adjacency matrix");
        if (options.vertices && options.vertices != r) throw std::runtime_error("--vertices disagrees with matrix dimensions");
        n = r;
        for (std::uint64_t k = 0; k < count; ++k) {
            if (!content(file, line)) throw std::runtime_error("Too few Matrix Market entries");
            std::istringstream row(line);
            std::string a, b, value;
            row >> a >> b;
            if (!row) throw std::runtime_error("Invalid Matrix Market entry");
            double weight = 1;
            if (field != "pattern") {
                row >> value;
                if (!row) throw std::runtime_error("Missing matrix value");
                std::size_t end = 0;
                weight = std::stod(value, &end);
                if (end != value.size() || !std::isfinite(weight)) throw std::runtime_error("Invalid matrix value");
            }
            if (row >> extra) throw std::runtime_error("Extra Matrix Market columns");
            auto source = vertex(a, 1), destination = vertex(b, 1);
            if (source >= n || destination >= n) throw std::runtime_error("Matrix endpoint exceeds dimensions");
            if (weight != 0) {
                edges.emplace_back(source, destination);
                if (symmetry == "symmetric" && source != destination) edges.emplace_back(destination, source);
            }
        }
        if (content(file, line)) throw std::runtime_error("Too many Matrix Market entries");
    } else {
        file.clear();
        file.seekg(0);
        while (content(file, line)) {
            std::string a, b, extra;
            std::istringstream row(line);
            row >> a >> b;
            if (!row || row >> extra) throw std::runtime_error("Edge lists require exactly two columns: source destination");
            auto source = vertex(a, options.index_base), destination = vertex(b, options.index_base);
            edges.emplace_back(source, destination);
            std::size_t required = static_cast<std::size_t>(std::max(source, destination)) + 1;
            if (options.vertices && required > options.vertices) throw std::runtime_error("Edge endpoint exceeds --vertices");
            n = std::max(n, required);
        }
    }
    if (file.bad()) throw std::runtime_error("Graph read failed: " + path);
    return Graph::from_edges(n, edges);
}
} // namespace pr
