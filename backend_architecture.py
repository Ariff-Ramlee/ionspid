import matplotlib.pyplot as plt

def draw_backend_architecture():
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    def draw_box(x, y, text, color="lightblue", width=2.2, height=0.8):
        box = plt.Rectangle((x, y), width, height, fc=color, ec="black", lw=1.2)
        ax.add_patch(box)
        ax.text(x + width/2, y + height/2, text, ha="center", va="center", fontsize=9, wrap=True)
        return (x, y, width, height)

    # Entry point
    server = draw_box(4, 8.5, "server.js\n(Entry Point)", "lightblue")

    # Express App Layer
    express = draw_box(4, 7, "Express App\n(Middleware + Routing)", "lightyellow")

    # Routes and Controllers
    routes = draw_box(2, 5.5, "routes/\n(Define Endpoints)", "lightgreen")
    controllers = draw_box(6, 5.5, "controllers/\n(Business Logic)", "lightgreen")

    # File Handling
    uploads = draw_box(4, 4, "uploads/\n(File Storage)", "lightpink")

    # Config
    pkg = draw_box(8, 2.5, "package.json\n(Dependencies + Config)", "lightgrey")

    # Draw arrows
    def arrow(src, dst):
        sx, sy, sw, sh = src
        dx, dy, dw, dh = dst
        ax.annotate("",
            xy=(dx + dw/2, dy + dh), xycoords="data",
            xytext=(sx + sw/2, sy), textcoords="data",
            arrowprops=dict(arrowstyle="->", lw=1.2))

    arrow(server, express)
    arrow(express, routes)
    arrow(express, controllers)
    arrow(express, uploads)
    arrow(express, pkg)

    plt.title("Backend System Architecture", fontsize=14, weight="bold")
    plt.show()

# Run the diagram
draw_backend_architecture()
