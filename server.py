#!/usr/bin/python3

import os
import requests
import flask
import werkzeug
import argparse
import sys
import json
import datetime
import yaml
import urllib
from bs4 import BeautifulSoup

import sqlalchemy
from sqlalchemy import Column, Integer, String, Boolean, or_, and_, asc, desc
from flask_sqlalchemy import SQLAlchemy

XAUTH_GROUPS_SEP = ","
TILES_CONFIG_FILE_PATH = "config.yaml"

app = flask.Flask("Atlantis Hub")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLITE_LOCATION") or "sqlite:///sqlite.db"
db = SQLAlchemy(app)

class Tile(db.Model):

    __tablename__ = "tiles"

    name        = Column(String, primary_key=True)
    common_name = Column(String)
    href        = Column(String)

def parse_xauth_groups(groups_string):

    if not groups_string:
        return []
    
    # format ist like this group1,group2,role:role1,role:role2,...
    # lets ignore the roles for now
    return filter(lambda x: "role:" not in x, groups_string.split(XAUTH_GROUPS_SEP))

def parse_tiles_file():

    with open(TILES_CONFIG_FILE_PATH) as f:
        return yaml.safe_load(f)

def filter_tiles_by_groups(tiles, groups):
    '''Remove all tiles that are not covered by the users groups'''
    return filter(lambda tile: not tile.get("groups") or tile.get("groups") in groups, tiles)

def cache_og_meta_icons(tiles):

    # TODO caching not working
    # TODO make sure errors are not constantly reloaded
    cache_path  = "./static/cache/"
    static_path = "./static/icons/"
   
    # TODO send only head request
    # TODO identify ourself as an og preview fetcher
    for tile_id in tiles.keys():
        if os.path.isfile("./static/static/{}.png".format(tile_id)):
            tiles[tile_id].update({ "icon" : "/static/static/{}.png".format(tile_id)})
            print("Found static icon for {}".format(tile_id))
        elif os.path.isfile("./static/cache/{}.png".format(tile_id)):
            print("Found cached icon for {}".format(tile_id))
            tiles[tile_id].update({ "icon" : "./static/icons/{}.png".format(tile_id)})
        else:
            try:
                content = urllib.request.urlopen(tiles[tile_id]["href"])
                content = requests.get(tiles[tile_id]["href"], allow_redirects=True).content
                soup = BeautifulSoup(content, "lxml")
                url = soup.find("meta", property="og:image")
                if url and url.get("content"):
                    print("Found image for {} at {}".format(tile_id, url))
                    with open("./static/cache/{}.png".format(tile_id), "wb") as f:
                        image = urllib.request.urlopen(url.get("content")).read()
                        image = requests.get(url.get("content"))
                        f.write(image)
                    tiles[tile_id].update({ "icon" : "./static/cache/{}.png".format(tile_id)})
                else:
                    print("Not tag found for {}".format(tile_id))
            except urllib.error.HTTPError as e:
                print("Error fetching {}. Skipping...".format(tile_id))
                continue

@app.route("/user-update")
def user_update():

    # show unavailable
    # show external
    # hidelist
    pass

@app.route("/")
def list():
    user = flask.request.headers.get("X-Forwarded-Preferred-Username")
    groups = parse_xauth_groups(flask.request.headers.get("X-Auth-Request-Groups"))

    tiles = parse_tiles_file()
    cache_og_meta_icons(tiles)
    print(json.dumps(tiles, indent=2))
    #tiles_filtered = filter_tiles_by_groups(tiles, groups)

    return flask.render_template("dashboard.html", tiles=tiles) # TODO use filtered tiles after testing

def create_app():
    db.create_all()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='AtlantisHub Server',
                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # general parameters #
    parser.add_argument("-i", "--interface", default="127.0.0.1", help="Interface to listen on")
    parser.add_argument("-p", "--port",      default="5000",      help="Port to listen on")
    args = parser.parse_args()

    # startup #
    with app.app_context():
        create_app()

    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host=args.interface, port=args.port, debug=True)
