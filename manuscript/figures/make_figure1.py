from pathlib import Path
from xml.sax.saxutils import escape


OUT = Path(__file__).resolve().parent / "figure1_architecture.svg"


BOXES = [
    ("Historical event log L", ["Cases, activities, resources", "Start and end timestamps", "Observed handovers"], 40, 55, 205, 125, "#e8f4f8"),
    ("Log-derived profiles", ["Resource capabilities", "Service-time samples", "Case arrivals and waits", "Handover priors"], 295, 45, 230, 145, "#eaf7ea"),
    ("Simulation environment", ["Case state", "Enabled activity", "Feasible action set", "Workload and memory"], 575, 45, 230, 145, "#fff3df"),
    ("Decision layer", ["Central baseline", "Agent-profile policy", "Constrained LLM-agent proxy"], 855, 45, 235, 145, "#f4ecf7"),
    ("Guardrails", ["Action mask", "Distributional penalty", "Fallback rule"], 595, 275, 205, 115, "#fdecea"),
    ("Outputs O = L', R', H'", ["Simulated event log L'", "Reasoning log R'", "Handover log H'"], 855, 265, 235, 130, "#edf0fb"),
    ("Validation", ["Prototype distances", "Chapela-Campa metrics", "Failure-mode analysis"], 295, 270, 230, 130, "#f2f2f2"),
]


ARROWS = [
    (245, 118, 295, 118, None, False),
    (525, 118, 575, 118, None, False),
    (805, 118, 855, 118, None, False),
    (972, 190, 972, 265, None, False),
    (800, 333, 855, 333, None, False),
    (855, 330, 525, 330, "event log quality", False),
    (695, 275, 895, 190, "constraints", False),
    (410, 270, 410, 190, "design feedback", True),
    (525, 337, 595, 337, "diagnostics", True),
]


def text(x, y, value, size=14, weight="400", anchor="start"):
    return (
        f'<text x="{x}" y="{y}" font-family="Arial, DejaVu Sans, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="#1f2d3d">'
        f"{escape(value)}</text>"
    )


def box(title, lines, x, y, w, h, fill):
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="#34495e" stroke-width="1.6"/>',
        text(x + w / 2, y + 28, title, 15, "700", "middle"),
    ]
    for i, line in enumerate(lines):
        parts.append(text(x + 18, y + 58 + i * 21, line, 13))
    return "\n".join(parts)


def arrow(x1, y1, x2, y2, label=None, dashed=False):
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    parts = [
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#34495e" stroke-width="1.6" marker-end="url(#arrow)"{dash}/>'
    ]
    if label:
        parts.append(
            text((x1 + x2) / 2, (y1 + y2) / 2 - 8, label, 12, "400", "middle")
        )
    return "\n".join(parts)


def main():
    body = []
    body.append(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1160" height="500" viewBox="0 0 1160 500" role="img" aria-label="Architecture diagram for resource-centric LLM-augmented process simulation">'
    )
    body.append(
        """
<defs>
  <marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto" markerUnits="strokeWidth">
    <path d="M0,0 L10,4 L0,8 Z" fill="#34495e" />
  </marker>
</defs>
<rect x="0" y="0" width="1160" height="500" fill="#ffffff"/>
"""
    )
    for item in BOXES:
        body.append(box(*item))
    for item in ARROWS:
        body.append(arrow(*item))
    body.append(text(40, 462, "Figure 1. Log-grounded architecture for resource-centric LLM-augmented process simulation.", 15, "700"))
    body.append("</svg>\n")
    OUT.write_text("\n".join(body), encoding="utf-8")


if __name__ == "__main__":
    main()
