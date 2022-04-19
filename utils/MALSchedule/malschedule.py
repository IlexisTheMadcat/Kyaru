from multiprocessing.sharedctypes import Value
import requests
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

# from utils import convert_list_iterator (doesn't work for some reason on Kyaru)
# ----------------------
def convert(iterator) -> list:
    new_list = [i for i in iterator]
    while "\n" in new_list:
        new_list.remove("\n")

    return new_list
# ----------------------


class _FetchError(Exception):
    pass


@dataclass
class Anime:
    name: str
    broadcasters: str
    tags: list
    image_url: str
    score: float
    mal_members: int
    synopsis: str
    metadata: dict
    estimated_rating: str


class MALSchedule:
    def __init__(self):
        self.previous_fetch = None

    def request_schedule(self):
        response = requests.get("https://myanimelist.net/anime/season/schedule")
        if response.status_code != 200:
            raise _FetchError("MAL did not return a status code of 200.")

        html = response.content
        soup = BeautifulSoup(html, "html.parser")

        entries = dict()

        week_data: Tag = soup.find("div", class_="js-categories-seasonal")

        passed_article = False
        for ind, day_data in enumerate(convert(week_data.children)):
            if passed_article:
                ind = ind-1
            if day_data.name == "article": 
                passed_article = True
                continue

            anime = dict()
            
            for anime_entry in convert(day_data.children):
                try: anime_entry["class"]
                except KeyError: continue

                try: anime_entry["style"]
                except KeyError: pass
                else: 
                    if "display: none" in anime_entry["style"]: continue

                if "anime-header" in anime_entry["class"]:
                    weekday = anime_entry.text
                    if weekday not in entries:
                        entries[weekday] = list()

                if all([i in anime_entry.attrs["class"] for i in ["seasonal-anime", "js-seasonal-anime"]]):
                    anime["name"] = anime_entry.find("div", class_=""
                                              ).find("div", class_="title"
                                              ).find("div", class_="title-text"
                                              ).find("h2", class_="h2_anime_title"
                                              ).a.text

                    broadcasters = anime_entry.find("div", class_=""
                                             ).find("div", class_="prodsrc"
                                             ).find("div", class_="broadcast")
                    
                    anime["broadcasters"] = []
                    if broadcasters.find("a"):
                        #print(convert(broadcasters.children))
                        for ind, broadcaster in enumerate(convert(broadcasters.children)):
                            if ind == 0: continue  # first element is a javascript modal of broadcaster information
                            if ind % 2 != 0: continue  # every other element is a space for some reason
                            anime["broadcasters"].append(broadcaster["title"])

                    anime["tags"] = []
                    for tag_element in convert(
                        anime_entry.find("div", class_=""
                                  ).find("div", class_="genres js-genre"
                                  ).find("div", "genres-inner js-genre-inner"
                                  ).children):
                        if tag_element == "-": continue
                        anime["tags"].append(tag_element.find("a")["title"])
                           
                    img = anime_entry.find("div", class_="image").a.img
                    if "src" in img.attrs:
                        anime["image_url"] = anime_entry.find("div", class_="image").a.img.attrs['src']
                    elif "data-src" in img.attrs: anime["image_url"] = anime_entry.find("div", class_="image").a.img.attrs['data-src']
                    else: anime["image_url"] = "about:blank"

                    try: anime["score"] = float(
                        anime_entry.find("div", class_="information"
                                  ).find("div", class_="scormem"
                                  ).find("div", title="Score"
                                  ).text.strip()
                    )
                    except ValueError: anime["score"] = 0

                    try: anime["mal_members"] = int(
                        anime_entry.find("div", class_="information"
                                  ).find("div", class_="scormem"
                                  ).find("div", title="Members"
                                  ).text.replace(",", "").strip("\n").strip().replace("K", "000")
                        )
                    except ValueError: anime["mal_members"] = 0

                    anime["synopsis"] = anime_entry.find("div", class_="synopsis js-synopsis"
                                                  ).find("p", class_="preline"
                                                  ).text.replace("\r", "")
                        
                    anime["metadata"] = dict()
                    for i in anime_entry.find("div", class_="synopsis js-synopsis").find_all("p", class_="mb4 mt8"):
                        anime["metadata"][i.span.text.strip(":")] = i.a.text.strip()
                   
                    # !!! Ratings are not from the MPAA. These are just suggestions based on given data.
                    if "Demographic" in anime["metadata"] and anime["metadata"]["Demographic"] == "Kids":
                        anime["estimated_rating"] = "G"
                    if "Action" in anime["tags"] or "Horror" in anime["tags"]:
                        anime["estimated_rating"] = "PG-13"
                    if "Ecchi" in anime["tags"]:
                        anime["estimated_rating"] = "R"
                    if "Hentai" in anime["tags"] or "Erotica" in anime["tags"]:
                        anime["estimated_rating"] = "NC-17"
                    if "estimated_rating" not in anime:
                        anime["estimated_rating"] = "PG"

                    entries[weekday].append(Anime(**anime))

        return entries


from discord.ext.commands.cog import Cog
from discord.ext.commands.core import (
    has_permissions, 
    bot_has_permissions, 
    command
)

class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(Commands(bot))