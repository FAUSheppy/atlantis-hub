#!/usr/bin/python3

import re
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
import urllib.parse
from bs4 import BeautifulSoup

import sqlalchemy
from sqlalchemy import Column, Integer, String, Boolean, or_, and_, asc, desc
from flask_sqlalchemy import SQLAlchemy

import imagetools

XAUTH_GROUPS_SEP = ","
TILES_CONFIG_FILE_PATH = "config.yaml"

USER_AGENT_HEADER  = 'User-Agent'
USER_AGENT_CONTENT = 'AtlantisHub:og-tag-query'

app = flask.Flask("Atlantis Hub")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLITE_LOCATION") or "sqlite:///sqlite.db"
db = SQLAlchemy(app)

class CacheInfo(db.Model):

    __tablename__ = "cache_info"

    href        = Column(String, primary_key=True)
    last_try    = Column(String)
    filepath    = Column(String) # None if failed
    source_type = Column(String) # og, rel-icon

class ColorCache(db.Model):

    __tablename__ = "color_cache"

    tile_id     = Column(String, primary_key=True)
    left_color  = Column(String)
    right_color = Column(String)
    fixed_bg    = Column(Boolean)

def record_cache_result(href, path, source_type=None):

    now = datetime.datetime.now().isoformat()
    ci = CacheInfo(href=href, filepath=path, last_try=now, source_type=source_type)
    db.session.merge(ci)
    db.session.commit()

def check_cache_for(href):
    '''Return the age of the cache in days or None'''

    result = db.session.query(CacheInfo).filter(CacheInfo.href==href).first()

    if not result:
        return -1

    last_try = datetime.datetime.fromisoformat(result.last_try)
    delta = datetime.datetime.now() - last_try

    return delta.days


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
    return list(filter(lambda x: "role:" not in x, groups_string.split(XAUTH_GROUPS_SEP)))

def parse_tiles_file():

    with open(TILES_CONFIG_FILE_PATH) as f:
        return yaml.safe_load(f)

def filter_tiles_by_groups(tiles, groups):
    '''Remove all tiles that are not covered by the users groups'''
    return filter(lambda tile: not tile.get("groups") or tile.get("groups") in groups, tiles)

def cache_og_meta_icons(tiles):

    CACHE_DIR  = "./static/cache/"
    STATIC_DIR = "./static/icons/"
   
    # TODO send only head request
    for tile_id in tiles.keys():
       
        href = tiles[tile_id]["href"]

        # use another url of a site for icon i.e. to query the github icon #
        # instead of a persons private profile picture (optional) #
        if tiles[tile_id].get("icon-alt-url"):
            href = tiles[tile_id].get("icon-alt-url")

        icon_name   = "{}.png".format(tile_id)
        static_path = os.path.join(STATIC_DIR, icon_name)
        cache_path  = os.path.join(CACHE_DIR, icon_name)

        cache_age = check_cache_for(href)

        if os.path.isfile(static_path):
            tiles[tile_id].update({ "icon" : static_path})
        elif os.path.isfile(cache_path):
            tiles[tile_id].update({ "icon" : cache_path})
        elif cache_age > 0 and cache_age < 30:
            continue
        else:
            try:

                # request page #
                urllib_request = urllib.request.Request(href)
                # some websites (e.g. Medium) don't like an empty user agent #
                # let's be honest about what we are doing #
                urllib_request.add_header(USER_AGENT_HEADER, USER_AGENT_CONTENT)
                og_response = urllib.request.urlopen(urllib_request)
                # og_response = requests.get(href, allow_redirects=True)
                soup = BeautifulSoup(og_response, "lxml")

                # look for og:image tag #
                og_image_tag = soup.find("meta", property="og:image")

                # look for link rel icon tag #
                # TODO maybe not just take first #
                links = soup.find_all('link', attrs={'rel': re.compile("^(shortcut icon|icon)$", re.I)})
                if len(links) > 0:
                    rel_icon_field = links[0]
                else:
                    rel_icon_field = None

                source_type = None

                # if image tag exists request the image-url #
                if og_image_tag and og_image_tag.get("content"):

                    try:

                        og_image_href = og_image_tag.get("content")

                        parsed_tag_url = urllib.parse.urlparse(og_image_href)
                        original_request_url = urllib.parse.urlparse(href)

                        if not parsed_tag_url.netloc or not parsed_tag_url.scheme:
                            og_image_href = "{}://{}{}".format(original_request_url.scheme,
                                original_request_url.netloc, parsed_tag_url.path)

                        try:
                            urllib_image_request = urllib.request.Request(og_image_href)
                            urllib_image_request.add_header(USER_AGENT_HEADER, USER_AGENT_CONTENT)
                            image = urllib.request.urlopen(urllib_image_request).read()
                        except urllib.error.URLError as e:
                            print("Failed to query og-image-tag [{}]:".format(og_image_href), e)

                        with open(cache_path, "wb") as f:
                            f.write(image)
                        
                        source_type = "og"
                    except urllib.error.HTTPError as e:
                        print("og:image tag present but download failed: {} ({})".format(e, href))

                elif rel_icon_field and rel_icon_field.get("href"):

                    icon_base_href = rel_icon_field["href"]
                    is_absolute = bool(urllib.parse.urlparse(icon_base_href).netloc)
                    if not is_absolute:
                        # get scheme + netloc from href
                        icon_base_href_parsed = urllib.parse.urlparse(href)
                        icon_fq_href = "{scheme}://{netloc}/{path}".format(
                                            scheme=icon_base_href_parsed.scheme,
                                            netloc=icon_base_href_parsed.netloc,
                                            path=icon_base_href.lstrip("/"))
                    else:
                        icon_fq_href = icon_base_href

                    # download icon #
                    image_response = requests.get(icon_fq_href)

                    with open(cache_path, "wb") as f:
                        f.write(image_response.content)
                    
                    source_type = "rel-icon"
                
                # record cache path in dict and db#
                if source_type:
                    tiles[tile_id].update({ "icon" : cache_path})
                    record_cache_result(href, cache_path, source_type)
                else:
                    # nothing found #
                    record_cache_result(href, None, None)

            except urllib.error.HTTPError as e:
                record_cache_result(href, None, None)
                continue

def cache_tile_gradients(tiles):

    for tile_id, values in tiles.items():

        result = db.session.query(ColorCache).filter(ColorCache.tile_id == tile_id).first()
        if result:
            if result.fixed_bg or values.get("background"):
                continue
            else:
                left_color = result.left_color
                right_color = result.right_color
        else:
            icon_path = values["icon"]
            left_color, right_color = imagetools.get_gradient_colors(icon_path)
            color_cache = ColorCache(tile_id=tile_id, right_color=right_color,
                                        left_color=left_color)
            db.session.merge(color_cache)
            db.session.commit()

        values.update({ "gradient-left" : left_color })
        values.update({ "gradient-right" : right_color })

@app.route("/user-update")
def user_update():

    # show unavailable
    # show external
    # hidelist
    pass

@app.route("/")
def dashboard():

    user = flask.request.headers.get("X-Forwarded-Preferred-Username")
    groups = parse_xauth_groups(flask.request.headers.get("X-Forwarded-Groups"))

    # load tiles #
    tiles = parse_tiles_file()
    cache_og_meta_icons(tiles)
    cache_tile_gradients(tiles)

    # build categories #
    categories = dict()
    for k,v in tiles.items():
        tags = v["tags"]
        main_tag = tags[0]

        # filter out non-display groups #
        if v["groups"] and not any([ g in v["groups"] for g in groups]):
            print(groups, v["groups"])
            continue

        if main_tag in categories:
            categories[main_tag].update({k : v})
        else:
            categories.update({ main_tag : {k : v}})

    return flask.render_template("dashboard.html", tiles=tiles, categories=categories,
                user=user, groups=groups, flask=flask)

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
