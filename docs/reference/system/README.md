# System Reference

Start with [System Overview](SYSTEM_OVERVIEW.md), then [Module Map](MODULE_MAP.md) and [Dependency Rules](DEPENDENCY_RULES.md). Open the detailed contract that answers the change you are making.

| Question | Document |
|---|---|
| What does each domain own? | [Domain Model](DOMAIN_MODEL.md) |
| Which principles constrain implementation? | [Architecture Principles](ARCHITECTURE_PRINCIPLES.md) |
| How does the analytical engine plan and compute? | [Market Analysis Architecture](MARKET_ANALYSIS_ARCHITECTURE.md) |
| How are time, availability and alignment handled? | [Time and Alignment](TIME_AND_ALIGNMENT.md) |
| Which numeric/data representation belongs where? | [Data Representation Policy and current status](DATA_REPRESENTATION_POLICY.md) |
| What is an execution-scoped analytical workspace? | [Analysis Workspace and Derived Data](ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md) |
| What are its detailed result and view contracts? | [Core](ANALYSIS_WORKSPACE_CORE.md), [Views and lifecycle](ANALYSIS_VIEWS_AND_LIFECYCLE.md) |
| Where do user-owned datasets and definitions live? | [User Workspace](USER_WORKSPACE.md) |

`AnalysisWorkspace` is an execution-scoped analytical object. The `user_data/` workspace is a storage boundary; the two are distinct.
