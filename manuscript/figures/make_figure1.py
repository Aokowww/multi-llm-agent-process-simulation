from pathlib import Path
from xml.sax.saxutils import escape


OUT = Path(__file__).resolve().parent / "figure1_architecture.svg"


BOXES = [
    ("Historical event log L", ["Cases and activities", "Resources and timestamps", "Observed handovers"], 35, 45, 205, 125, "#e8f4f8"),
    ("Log-derived profiles", ["Resource capabilities", "Service-time samples", "Arrivals and waits", "Handover priors"], 285, 35, 230, 145, "#eaf7ea"),
    ("Simulation environment", ["Case state", "Enabled activity", "Feasible action set", "Workload and memory"], 560, 35, 230, 145, "#fff3df"),
    ("Policy layer", ["Central baseline", "Agent-profile policy", "LLM-agent proxy", "Optional real LLM"], 835, 35, 250, 145, "#f4ecf7"),
    ("Guardrails", ["Action mask", "JSON validation", "Distributional penalty", "Fallback rule"], 580, 270, 225, 135, "#fdecea"),
    ("Outputs O = L', R', H'", ["Simulated event log L'", "Reasoning log R'", "Handover log H'"], 835, 275, 250, 130, "#edf0fb"),
    ("Dual evaluation", ["BPS log quality", "LLM-agent behavior", "What-if response"], 285, 270, 230, 130, "#f2f2f2"),
]


ARROWS = [
    (240, 108, 285, 108, None, False),
    (515, 108, 560, 108, None, False),
    (790, 108, 835, 108, None, False),
    (960, 180, 960, 275, None, False),
    (805, 337, 835, 337, None, False),
    (692, 270, 920, 180, "constraints", False),
    (400, 270, 400, 180, "design feedback", True),
    (515, 337, 580, 337, None, True),
]


PATH_ARROWS = [
    ("M 960 405 L 960 430 L 400 430 L 400 400", "generated logs and traces", 680, 421, False),
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


def path_arrow(path, label=None, label_x=0, label_y=0, dashed=False):
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    parts = [
        f'<path d="{path}" fill="none" stroke="#34495e" stroke-width="1.6" marker-end="url(#arrow)"{dash}/>'
    ]
    if label:
        parts.append(text(label_x, label_y, label, 12, "400", "middle"))
    return "\n".join(parts)


def main():
    body = []
    body.append(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1160" height="470" viewBox="0 0 1160 470" role="img" aria-label="Architecture diagram for resource-centric LLM-augmented process simulation">'
    )
    body.append(
        """
<defs>
  <marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto" markerUnits="strokeWidth">
    <path d="M0,0 L10,4 L0,8 Z" fill="#34495e" />
  </marker>
</defs>
<rect x="0" y="0" width="1160" height="470" fill="#ffffff"/>
"""
    )
    for item in BOXES:
        body.append(box(*item))
    for item in ARROWS:
        body.append(arrow(*item))
    for item in PATH_ARROWS:
        body.append(path_arrow(*item))
    body.append("</svg>\n")
    OUT.write_text("\n".join(body), encoding="utf-8")


if __name__ == "__main__":
    main()
