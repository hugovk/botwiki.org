#!/usr/bin/env python
"""
Create markdown entries and screenshots from submissions to:
https://botwiki.org/submit-your-bot
So far only Twitter bots are supported.
"""
from __future__ import print_function, unicode_literals
import argparse
import datetime
import gspread  # pip install gspread
import json
import os
from oauth2client.client import SignedJwtAssertionCredentials

# from pprint import pprint


def make_twitter_url(text, force_it=False):
    """ Do the best to turn it into a Twitter URL """
    if text.startswith("twitter.com"):
        return "https://" + text.replace(" ", "")
    if text.startswith("https://twitter.com"):
        return text.replace(" ", "")
    if text.startswith("@"):
        return "https://twitter.com/" + text[1:].replace(" ", "")
    if force_it:
        return "https://twitter.com/" + text.replace(" ", "")
    return text


def validate_creator_twitter_url(url):
    """ Validate url to return a Twitter URL """
    return make_twitter_url(url, force_it=True)


def validate_location(location):
    """ Validate location to return a URL """
    return make_twitter_url(location)


def bot_category(bot):
    """ Get the bot's category from its location """
    if "twitter.com" in bot['location']:
        return "twitterbots"
    return None


def bot_network(bot):
    """ Get the bot's network from its location """
    if "twitter.com" in bot['location']:
        return "Twitter"
    return None


def dedupe(seq):
    """ Dedupe a list, preserving order """
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def bot_tags(bot):
    """ Add network-specific tags, remove duplicates """
    tags_to_add = []
    if "twitter.com" in bot['location']:
        tags_to_add = ["twitter", "twitterbot"]

    # Remove spaces after commas, but not from tags, and convert into a list
    user_tags = bot['tags'].replace(", ", ",").split(",")

    # Add user tags
    tags_to_add.extend(user_tags)

    # Add open-source tags
    if 'is_open_source' in bot and bot['is_open_source']:
        tags_to_add.extend(["open source", "opensource"])
        if 'open_source_language' in bot and bot['open_source_language']:
            tags_to_add.append(bot['open_source_language'])

    # Add author's Twitter username
    if 'creator_twitter_url' in bot and bot['creator_twitter_url']:
        tags_to_add.append(
            twitter_username_from_url(bot['creator_twitter_url']))

    # Remove duplicates
    tags_to_add = dedupe(tags_to_add)

    # And back to a lowercase string
    return ",".join(tags_to_add).lower()


def bot_type(bot):
    """ Get the bot's type from its location """
    if "twitter.com" in bot['location']:
        return "twitterbots"
    return None


def twitter_username_from_url(url, at_sign=False):
    """ Get a Twitter username from a URL """
    username = url.rsplit('/', 1)[-1]
    if at_sign:
        username = "@" + username
    return username


def bot_username(bot, at_sign=False):
    """ Get the bot's username from its location """
    username = None
    if "twitter.com" in bot['location']:
        username = twitter_username_from_url(bot['location'])
    return username


def format_md(bot):
    """
    bot.network will be deduced based on the URL, eg
    bot.url contains youtube.com => bot.network = 'YouTube'
    and bot.category = 'youtube-bots'
    and bot.type = 'youtubebot'
    etc.
    """

    date = datetime.datetime.today()
    date = date.strftime("%B %d, %Y")

    bot['category'] = bot_category(bot)
    bot['network'] = bot_network(bot)
    bot['tags'] = bot_tags(bot)
    bot['type'] = bot_type(bot)
    bot['username'] = bot_username(bot, at_sign=True)

    if bot['is_open_source']:
        open_source_text = 'n [open source](' + bot['source_url'] + ') '
    else:
        open_source_text = ' '

    if 'creator_twitter_url' in bot:
        creator_text = ('[' + bot['creator'] + ']('
                        + bot['creator_twitter_url'] + ')')
    else:
        creator_text = bot['creator']

    md_file_text = (
        '/*\n'
        + 'Title: ' + bot['username'] + '\n'
        + 'Description: ' + bot['short_description'] + '\n'
        + 'Author: botsheeter.py' + '\n'
        + 'Date: ' + date + '\n'
        + 'Tags: ' + bot['tags'] + '\n'
        + 'Nav: hidden' + '\n'
        + 'Robots: index,follow' + '\n'
        + '*/' + '\n\n'
        + '[![](/' + bot_png_filename(bot) + ')](' + bot['location'] + ')\n\n'
        + '[' + bot['username'] + '](' + bot['location'] + ') is a'
        + open_source_text
        + bot['network'] + ' bot created by ' + creator_text + '. \n\n'
        + bot['description'] + '\n\n')
    return md_file_text


def bot_png_filename(bot):
    """ Return a filename for saving this bot's png file """
    return ("content/bots/" + bot_type(bot) + "/images/" + bot_username(bot)
            + ".png")


def bot_md_filename(bot):
    """ Return a filename for saving this bot's md file """
    return "content/bots/" + bot_type(bot) + "/" + bot_username(bot) + ".md"


def create_dirs(dir):
    """ Makes all intermediate-level directories if needed """
    if not os.path.isdir(dir):
        os.makedirs(dir)


def save_md(md_file_text, filename):
    """ Save the md_file_text into filename """
    create_dirs(os.path.dirname(filename))
    print("Saving to", filename)
    with open(filename, "w") as f:
        f.write(md_file_text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create markdown and screenshots from botwiki submissions",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-j', '--json',
        default='E:/Users/hugovk/Dropbox/bin/data/botsheeter.json',
        help="JSON file location containing Google OAuth credentials from: "
             "https://gspread.readthedocs.org/en/latest/oauth2.html")
    args = parser.parse_args()

    json_key = json.load(open(args.json))
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = SignedJwtAssertionCredentials(
        json_key['client_email'], json_key['private_key'].encode(), scope)

    gc = gspread.authorize(credentials)

    wks = gc.open("Botwiki.org (Responses)").sheet1

    list_of_rows = wks.get_all_values()
    list_of_rows.pop(0)  # ditch header

    # Getting stuff to build .md -- only Twitter bots for now
    twitter_urls = []  # for screenshots
    for i, row in enumerate(list_of_rows):
        # row is a list of columns
        bot = {}
        bot['location'] = validate_location(row[1])
        if "twitter" in bot['location']:
            # if (row[11] == "TRUE" or row[11] == "DECLINED" or row[11]):
                # print("Already added or declined, skip it")
                # continue
            twitter_urls.append(bot['location'])
            bot['description'] = row[2]
            bot['tags'] = row[3]
            bot['active'] = row[4]
            if row[5]:
                bot['is_open_source'] = True
                bot['source_url'] = row[5]
            else:
                bot['is_open_source'] = False
            bot['creator'] = row[6]
            bot['short_description'] = row[7]
            bot['creator_twitter_url'] = validate_creator_twitter_url(row[8])
            # row[9] not used
            bot['open_source_language'] = row[10]

            outfile = bot_md_filename(bot)
            if os.path.isfile(outfile):
                continue  # Don't overwrite existing

            print(bot)
            md_file_text = format_md(bot)
            print()
            print(md_file_text)
            print()
            save_md(md_file_text, outfile)

            # Update the worksheet
            # * First value is row number but take care!
            #   - Rows begin at 1, not 0.
            #   - Don't forget we ditched the header, so i==0 is row 2.
            added_row = i + 2
            # * Second value is column (A=1, B=2, ..., L=12, etc.)
            added_col = 12
            wks.update_cell(added_row, added_col, "true")

    if twitter_urls:
        # Prep botshotter.py call
        print("Save images...")
        twitter_urls = ",".join(twitter_urls)
        import botshotter
        # TODO harcoded for Twitter:
        outdir = "content/bots/twitterbots/images/"
        create_dirs(outdir)
        botshotter.botshotter(twitter_urls, outdir, headless=True)

# End of file
