# Graph datasets

Generated/downloaded data is ignored by Git. Keep provenance beside real datasets and preserve SHA-256 hashes in each benchmark run. Dataset size alone does not establish cache residency; compare the working-set estimate with the actual node's caches.

## Synthetic controls

```sh
python3 scripts/generate_graph.py --kind uniform --vertices 100000 --edges 1000000 --seed 548 --output data/uniform.mtx
python3 scripts/generate_graph.py --kind skewed --vertices 100000 --edges 1000000 --seed 548 --output data/skewed.mtx
python3 scripts/generate_graph.py --kind hub --vertices 100000 --edges 1000000 --seed 548 --output data/hub.mtx
python3 scripts/generate_graph.py --kind local --vertices 100000 --edges 1000000 --seed 548 --output data/local.mtx
python3 scripts/generate_graph.py --kind local --vertices 100000 --edges 1000000 --seed 548 --permute --output data/local-permuted.mtx
```

The generators produce directed multigraphs with exactly the requested edge count. Uniform endpoints give relatively even incoming degrees. Skewed destinations use weights proportional to `(v+1)^-1.1`, concentrating expensive rows at low IDs. Hub graphs put about 90% of edges into one destination, exposing the indivisible-row limit. Local graphs connect each source to a destination within a ±64-ID window. `--permute` applies a fixed vertex permutation to the same generated topology using an independent random stream, preserving structural equivalence and degree distributions. The generator embeds its configuration in a Matrix Market comment, retains duplicates/self-loops, and refuses to replace existing output.

Repeat at multiple sizes, e.g. `(10^4,10^5)`, `(10^5,10^6)`, `(10^6,10^7)`, chosen to cross the compute node's cache capacities. These are controlled synthetic families, not validated generative models of web graphs.

## Public directed graphs

```sh
python3 scripts/fetch_dataset.py wiki-Vote
python3 scripts/fetch_dataset.py web-Google
build/pagerank --graph data/wiki-Vote.txt --strategy serial --verify
```

Sources: [SNAP Wikipedia vote network](https://snap.stanford.edu/data/wiki-Vote.html) and [SNAP Google web graph](https://snap.stanford.edu/data/web-Google.html). Follow the source pages' citation instructions in the final report. The fetcher records the URL, retrieval time and archive/uncompressed SHA-256. These hashes identify what was retrieved; they are not an independent publisher checksum.

The loader retains raw numeric IDs: gaps become isolated vertices and `n = max_ID+1` unless `--vertices` is supplied. SNAP's published number of active vertices can therefore differ from this program's n. This changes the teleport/dangling model; record the choice explicitly. To compare against a published active-vertex graph, compact endpoint IDs consistently with a saved mapping before benchmarking, and include externally declared isolated vertices if appropriate. Never silently compare results from different vertex universes.

No datasets are downloaded automatically during tests or builds. Review real datasets' indexing and directedness before running. See the top-level README for supported Matrix Market semantics, including row-to-column orientation and treatment of numeric values.
