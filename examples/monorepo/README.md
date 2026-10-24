# Example monorepo

A real, tiny monorepo with four Python services, used to try ShipKit.
It is an *example repo for the tool*, not data the tool ships with:
ShipKit's product code never reads this folder.

| Service | Path | Depends on |
|---|---|---|
| common | `libs/common` | - |
| api | `services/api` | common |
| worker | `services/worker` | common |
| gateway | `services/gateway` | api |

Each service has real code and real pytest tests. Run any of them:

```bash
cd services/api && python -m pytest tests -q
```

Try change-aware CI (needs Docker running, from a git clone of
this folder with a commit on a branch):

```bash
# change only services/api, then:
shipkit ci --base main          # runs api, then gateway (depends on api)
# change libs/common, then:
shipkit ci --base main          # runs common, then api+worker, then gateway
shipkit ci --base main --dry-run
```
