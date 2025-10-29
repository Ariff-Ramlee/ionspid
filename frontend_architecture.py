import matplotlib.pyplot as plt

def draw_frontend_architecture():
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Helper function to draw boxes
    def draw_box(x, y, text, color="lightblue", width=2.2, height=0.8):
        box = plt.Rectangle((x, y), width, height, fc=color, ec="black", lw=1.2)
        ax.add_patch(box)
        ax.text(x + width/2, y + height/2, text, ha="center", va="center", fontsize=9, wrap=True)
        return (x, y, width, height)

    # Main App.js
    app = draw_box(4, 8.5, "App.js\n(Main Entry Point)", "lightblue")

    # TopBar, Sidebar, Main Content
    topbar = draw_box(0.5, 7, "TopBar\n(Persistent Nav)", "lightyellow")
    sidebar = draw_box(4, 7, "Sidebar\n(Collapsible)", "lightyellow")
    maincontent = draw_box(7, 7, "Main Content Area\n(Routes Render Here)", "lightyellow")

    # Router and Pages
    router = draw_box(7, 5.5, "React Router", "lightpink")
    home = draw_box(5.5, 4, "Home Page", "white")
    upload = draw_box(7.5, 4, "Upload Page", "white")
    results = draw_box(9.5, 4, "Results Page", "white")
    wizard = draw_box(7, 2.5, "Analysis Wizard", "lightgreen")

    # Wizard steps
    step1 = draw_box(6, 1, "Step 1\n(Data Upload)", "white")
    step2 = draw_box(8, 1, "Step 2\n(Parameter Config)", "white")
    step3 = draw_box(10, 1, "Step 3\n(Preview/Results)", "white")

    # Database/State/Styling
    state = draw_box(1, 4, "State Management\n(useState in App.js)", "lightgrey")
    styling = draw_box(1, 2.5, "Styling\n(App.css, index.css)", "white")
    extensibility = draw_box(1, 1, "Extensible\n(New Pages / Wizard Steps)", "lightcyan")

    # Draw arrows
    def arrow(src, dst):
        sx, sy, sw, sh = src
        dx, dy, dw, dh = dst
        ax.annotate("",
            xy=(dx + dw/2, dy + dh), xycoords="data",
            xytext=(sx + sw/2, sy), textcoords="data",
            arrowprops=dict(arrowstyle="->", lw=1.2))

    # App connections
    arrow(app, topbar)
    arrow(app, sidebar)
    arrow(app, maincontent)

    # MainContent -> Router -> Pages
    arrow(maincontent, router)
    arrow(router, home)
    arrow(router, upload)
    arrow(router, results)
    arrow(router, wizard)

    # Wizard -> steps
    arrow(wizard, step1)
    arrow(step1, step2)
    arrow(step2, step3)

    # App -> State, Styling
    arrow(app, state)
    arrow(app, styling)
    arrow(router, extensibility)

    plt.title("Frontend System Architecture", fontsize=14, weight="bold")
    plt.show()

# Run the diagram
draw_frontend_architecture()
