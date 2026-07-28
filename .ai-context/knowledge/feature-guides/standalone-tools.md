# Standalone tools guide

Each utility is an independent entry point with its own requirements file where dependencies are needed. Before changing one:

1. Read its local README and requirements file.
2. Preserve its current CLI/GUI entry behavior.
3. Check platform assumptions and external side effects.
4. Run a focused syntax/import check when dependencies are available; there is no shared test harness.

Notable extension points include `CsvConverter.convert_file`, `cloc_visualizer.parse_data`, `SNMPExplorerApp`, the Minecraft modpack pipeline, and the Autotask Selenium helpers.
