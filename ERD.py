import matplotlib.pyplot as plt

def draw_database_erd():
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis("off")

    def draw_table(x, y, title, fields, color="lightyellow"):
        width, height = 2.5, 0.6 + 0.4 * len(fields)
        table = plt.Rectangle((x, y - height), width, height, fc=color, ec="black", lw=1.2)
        ax.add_patch(table)
        ax.text(x + width/2, y - 0.3, title, ha="center", va="top", fontsize=10, fontweight="bold")
        for i, field in enumerate(fields):
            ax.text(x + 0.1, y - 0.7 - 0.4 * i, field, ha="left", va="top", fontsize=8)
        return (x, y - height/2, width, height)

    # Draw tables
    users = draw_table(1, 9, "Users", ["user_id (PK)", "name", "email", "role"])
    projects = draw_table(5, 9, "Projects", ["project_id (PK)", "title", "description", "user_id (FK)"])
    samples = draw_table(9, 9, "Samples", ["sample_id (PK)", "project_id (FK)", "site", "date_collected"])
    files = draw_table(3, 5, "Files", ["file_id (PK)", "sample_id (FK)", "filename", "file_path", "file_type"])
    steps = draw_table(7, 5, "PipelineSteps", ["step_id (PK)", "project_id (FK)", "step_name", "parameters", "status"])
    results = draw_table(5, 2, "Results", ["result_id (PK)", "sample_id (FK)", "step_id (FK)", "output_path", "summary"])

    # Helper to draw relationships (lines with arrows)
    def connect(src, dst):
        sx, sy, sw, sh = src
        dx, dy, dw, dh = dst
        ax.annotate("",
            xy=(dx + dw/2, dy), xycoords="data",
            xytext=(sx + sw/2, sy - sh/2), textcoords="data",
            arrowprops=dict(arrowstyle="->", lw=1.2))

    # Relationships
    connect(users, projects)      # User -> Projects
    connect(projects, samples)    # Project -> Samples
    connect(samples, files)       # Sample -> Files
    connect(projects, steps)      # Project -> Steps
    connect(samples, results)     # Sample -> Results
    connect(steps, results)       # Step -> Results

    plt.title("Planned Database ERD", fontsize=14, weight="bold")
    plt.show()

# Draw the ERD
draw_database_erd()
