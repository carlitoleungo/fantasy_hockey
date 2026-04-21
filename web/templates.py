from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="web/templates")


def rank_color(rank, team_count):
    if rank is None or team_count is None:
        return ""
    if rank == 1:
        return "bg-green-100"
    if rank == team_count:
        return "bg-red-100"
    return ""


templates.env.filters["rank_color"] = rank_color
