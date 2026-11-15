"""Compose the materials pinned by one order-node contract in the research fixture."""
from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class Material:
    ref: str
    kind: str
    body: str
    marker: str
    source: str
    claims: tuple = ()  # Explicitly declared (subject, value), reviewed at publication.
    operation: str | None = None

    def __post_init__(self):
        declared = {}
        for subject, value in self.claims:
            if subject in declared and declared[subject] != value:
                raise ValueError("material declares incompatible values")
            declared[subject] = value

    @property
    def digest(self):
        return sha256(self.body.encode()).hexdigest()

    @property
    def publication_digest(self):
        manifest = {"ref": self.ref, "source": self.source, "kind": self.kind, "body_sha256": self.digest,
                    "claims": sorted(self.claims), "operation": self.operation}
        raw = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
        return sha256(raw).hexdigest()

    @property
    def size(self):
        return len(self.body.encode())


@dataclass(frozen=True)
class Contract:
    required: tuple
    optional: tuple  # ordered preference for this node and role
    operation: str


def select(issued, binding, actor, materials, pins, readable, commands):
    """Resolve the contract and cap from a platform-issued dispatch, never the request."""
    record = issued.get(binding["run"])
    if not record or record[0] != binding or actor != binding["member"] or not readable:
        return {"status": "blocked", "selected": [], "reason": "dispatch access unavailable"}
    _, contract, budget = record
    outcome = {"status": "blocked", "selected": [], "omitted": {}, "used_bytes": 0,
               "budget_bytes": budget, "unit": "UTF-8 material body bytes"}
    required = tuple(dict.fromkeys(contract.required))
    optional = tuple(ref for ref in dict.fromkeys(contract.optional) if ref not in required)

    def available(ref):
        material = materials.get(ref)
        return (ref in readable and material is not None and pins.get(ref) == material.publication_digest
                and (material.operation is None or material.operation in commands))

    if contract.operation not in commands or any(not available(ref) for ref in required):
        return dict(outcome, reason="required capability or material unavailable")
    facts = {}
    for ref in required:
        for subject, value in materials[ref].claims:
            if subject in facts and facts[subject][1] != value:
                return dict(outcome, reason="incompatible required instructions",
                            conflict={"subject": subject, "refs": [facts[subject][0], ref]})
            facts[subject] = (ref, value)
    required_bytes = sum(materials[r].size for r in required)
    used = required_bytes
    if used > budget:
        return dict(outcome, reason="required material exceeds budget", required_bytes=used)
    selected, omitted = list(required), {}
    for ref in optional:
        if not available(ref):
            # The externally visible result discloses no hidden optional material identifier.
            continue
        material = materials[ref]
        if any(k in facts and facts[k][1] != v for k, v in material.claims):
            omitted[ref] = "conflicts with selected instruction"
        elif used + material.size > budget:
            omitted[ref] = "optional material exceeds remaining budget"
        else:
            selected.append(ref)
            used += material.size
            for key, value in material.claims:
                facts[key] = (ref, value)
    return dict(outcome, status="ready", reason="ready", selected=selected,
                used_bytes=used, required_bytes=required_bytes, omitted=omitted)
