"""
Adult DVD Empire Metadata Agent for Plex

This script is tailored for the Plex Media Server environment and is written to be compatible with Python 2.7, as used by Plex's plug-in system. It adheres to the nuances of Plex's framework, especially the handling of HTTP requests, XML and HTML parsing, and Plex's metadata and agent structure.

Key Points:
- The script uses Plex's built-in libraries such as HTTP, HTML, and Util.
- It avoids features not supported in Plex's restricted Python environment (e.g., `any()`).
- Exception handling is broad due to Plex's limited error logging capabilities.
- Logging is done through Plex's Log() function for better integration.

Please ensure any modifications maintain compatibility with Python 2.7 and adhere to the restrictions of Plex's plugin system. Special care must be taken not to use modern Python features that are incompatible with this version.

Author: SlickRick
Date: April 24, 2024
Python Version: 2.7
"""
# Import required modules

import re
import datetime
import random
import urllib2

# Preferences
preference = Prefs
DEBUG = preference['debug']

def LogDebug(message):
    if DEBUG:
        Log('[DEBUG] ' + message)

LogDebug('Agent debug logging is enabled!' if DEBUG else 'Agent debug logging is disabled!')
studioascollection = preference['studioascollection']
searchtype = preference['searchtype'] if preference['searchtype'] != 'all' else 'allsearch'
LogDebug('Search Type: %s' % searchtype)

GOOD_SCORE = max(int(preference['goodscore'].strip()), 1)
LogDebug('Good Score Threshold: %i' % GOOD_SCORE)
INITIAL_SCORE = 100

ADE_BASEURL = 'http://www.adultdvdempire.com'
ADE_SEARCH_MOVIES = ADE_BASEURL + '/' + searchtype + '/search?view=list&q=%s'
ADE_MOVIE_INFO = ADE_BASEURL + '/%s/'

def Start():
    HTTP.CacheTime = CACHE_1MINUTE
    HTTP.Headers['User-agent'] = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)'
    LogDebug('HTTP headers set and cache time configured.')

def ValidatePrefs():
    LogDebug('Preferences validated.')

class ADEAgent(Agent.Movies):
    name = 'Adult DVD Empire'
    languages = [Locale.Language.English]
    primary_provider = True
    fallback_agent = ['com.plexapp.agents.themoviedb'] #Personal choice can be taken out
    accepts_from = ['com.plexapp.agents.localmedia']

    def search(self, results, media, lang):
        title = media.title

        # Check if title has {tmdb-} or {imdb-} tags and return immediately if found
        # Assume if {tmdb-} or {imdb-} tags are present, user wants to use another Plex Agent to manually match.
        if re.search(r'\{tmdb-\d+\}', title) or re.search(r'\{imdb-tt\d+\}', title):
            LogDebug('Title contains TMDB or IMDB tag, skipping search.')
            return

        special_id = None

        # Check for special ID and strip it from the title if present
        match = re.search(r'\{ade-(\d{7})\}', title)
        if match:
            special_id = match.group(1)
            title = re.sub(r'\s*\{ade-\d{7}\}\s*', '', title).strip()

        # Adjust title if it starts with 'The'
        if title.lower().startswith('the '):
            title = title[4:] + ', The'

        encoded_title = String.URLEncode(String.StripDiacritics(title.replace('-', '')))
        LogDebug('Formatted search query: {}'.format(encoded_title))
        search_url = ADE_SEARCH_MOVIES % encoded_title
        LogDebug('Constructed search URL: {}'.format(search_url))

        movie_dict = {}

        try:
            search_page = HTML.ElementFromURL(search_url)
            LogDebug('Search page successfully retrieved.')
            movies = search_page.xpath('//div[contains(@class,"row list-view-item")]')
            LogDebug('Found {} movies on the search page.'.format(len(movies)))

            for movie in movies:
                movie_title = movie.xpath('.//a[contains(@label,"Title")]')[0].text_content().strip()
                # Adjust title format if it ends with ', The'
                if movie_title.endswith(', The'):
                    movie_title = 'The ' + movie_title[:-5]
                
                movie_id = movie.xpath('.//a[contains(@label,"Title")]/@href')[0].split('/', 2)[1]
                dvd_elements = movie.xpath('.//a[@title="DVD" or @title="dvd"]')
                movie_format = 'DVD' if dvd_elements else 'VOD'
                
                # Extract year
                year_element = movie.xpath('.//small[contains(text(),"released")]/following-sibling::text()')
                cur_year = re.search(r'\d{2}/\d{2}/(\d{4})', year_element[0].strip() if year_element else '').group(1) if year_element else None
                
                # Adjust score based on special ID
                if special_id and movie_id == special_id:
                    score = 100
                else:
                    score = INITIAL_SCORE - Util.LevenshteinDistance(title.lower(), movie_title.lower())

                if (movie_title, cur_year) not in movie_dict:
                    movie_dict[(movie_title, cur_year)] = []
                movie_dict[(movie_title, cur_year)].append((movie_id, movie_format, score))

            # Process scoring adjustments for DVD and VOD entries
            for key, entries in movie_dict.items():
                dvd_present = False
                for entry in entries:
                    if entry[1] == 'DVD':
                        dvd_present = True
                        break
                
                if dvd_present:
                    for i, (id, format, score) in enumerate(entries):
                        if format == 'VOD':
                            entries[i] = (id, format, score // 2)
                            LogDebug('Adjusted VOD score for {}: {}'.format(key[0], score // 2))

            # Append results to Plex
            for key, movie_info in movie_dict.items():
                for id, format, score in movie_info:
                    title_with_year = "{} ({})".format(key[0], key[1]) if key[1] else key[0]  # Append year if available
                    results.Append(MetadataSearchResult(id=id, name=title_with_year, score=score, lang=lang))

            results.Sort('score', descending=True)
            LogDebug('Results sorted by score.')
        except urllib2.HTTPError as e:
            LogDebug('HTTP Error: %s - %s' % (e.code, search_url))
        except urllib2.URLError as e:
            LogDebug('URL Error: %s - %s' % (e.reason, search_url))
        except Exception as e:
            LogDebug('Failed to fetch or parse search results: %s' % str(e))

    def update(self, metadata, media, lang):
        LogDebug('Starting metadata update for ID: %s' % metadata.id)
        info_url = ADE_MOVIE_INFO % metadata.id
        LogDebug('Constructed movie info URL: %s' % info_url)
        
        try:
            info_page = HTML.ElementFromURL(info_url)
            LogDebug('Movie info page retrieved.')

            # Update movie title from the title from the media information
            import re
            title_without_year = re.sub(r"\s*\(\d{4}\)\s*$", "", media.title)  # Regex to remove year from the end
            metadata.title = title_without_year
            LogDebug('Updated movie title: %s' % metadata.title)

            # Tagline
            self.update_tagline(metadata, info_page)

            # Summary
            self.update_summary(metadata, info_page)

            # Rating
            self.update_rating(metadata, info_page)

            # Content Rating
            self.update_content_rating(metadata, info_page)

            # Studio
            self.update_studio(metadata, info_page)

            # Originally Available At
            self.update_originally_available_at(metadata, info_page)

            # Production Year
            self.update_year(metadata, info_page)

            # Thumbnail and Poster
            self.update_posters(metadata, info_page)

            # Update cast
            self.update_cast(metadata, info_page)

            # Update director
            self.update_director(metadata, info_page)

            # Update genres
            self.update_genres(metadata, info_page)

            # Additional metadata fields can be updated here...
            
        except urllib2.HTTPError as e:
            LogDebug('HTTP Error: %s - %s' % (e.code, info_url))
        except urllib2.URLError as e:
            LogDebug('URL Error: %s - %s' % (e.reason, info_url))
        except Exception as e:
            LogDebug('Failed to update metadata: %s' % str(e))

    def update_tagline(self, metadata, info_page):
        try:
            tagline_element = info_page.xpath('//h2[contains(@class, "test")]/text()')
            if tagline_element:
                tagline = tagline_element[0].strip()
                metadata.tagline = tagline
                LogDebug('Tagline Found and Set: %s' % metadata.tagline)
            else:
                LogDebug('No tagline element found.')
        except Exception as e:
            LogDebug('Exception while parsing tagline: %s' % str(e))

    def update_summary(self, metadata, info_page):
        try:
            summary_elements = info_page.xpath('//div[@class="synopsis-content"]/p')
            if summary_elements:
                summary = summary_elements[0].text_content().strip()
                metadata.summary = summary
                LogDebug('Summary Found and Set: %s' % summary)
            else:
                LogDebug('No summary elements found.')
        except Exception as e:
            LogDebug('Exception while parsing summary: %s' % str(e))

    def update_content_rating(self, metadata, info_page):
        try:
            # Extract content rating
            rating_element = info_page.xpath("//li[small[text()='Rating: ']]/small/following-sibling::text()")
            if rating_element:
                metadata.content_rating = rating_element[0].strip()
                LogDebug('Content Rating Found: {}'.format(metadata.content_rating))
            else:
                LogDebug('No Content Rating elements found.')
        except Exception as e:
            LogDebug('Exception while parsing content rating: %s' % str(e))
    
    def update_studio(self, metadata, info_page):
        try:
            studio_element = info_page.xpath("//li[small[text()='Studio: ']]/small/following-sibling::a/text()")
            if studio_element:
                metadata.studio = studio_element[0].strip()
                LogDebug('Studio Found: {}'.format(metadata.studio))
            else:
                LogDebug('No Studio elements found.')
        except Exception as e:
            LogDebug('Exception while parsing studio: %s' % str(e))
    
    def update_originally_available_at(self, metadata, info_page):
        try:
            release_element = info_page.xpath("//li[small[text()='Released:']]/small/following-sibling::text()")
            production_year_element = info_page.xpath("//li[small[text()='Production Year:']]/small/following-sibling::text()")

            release_date = None
            if release_element:
                release_date_str = release_element[0].strip()
                # Try different date formats
                date_formats = ["%b %d %Y", "%B %d, %Y", "%m/%d/%Y"]
                for date_format in date_formats:
                    try:
                        release_date = datetime.datetime.strptime(release_date_str, date_format)
                        break
                    except ValueError:
                        continue
                if release_date:
                    LogDebug('Release date parsed successfully: %s' % release_date.strftime('%Y-%m-%d'))
                else:
                    LogDebug('Failed to parse release date: %s' % release_date_str)                

            Production_year = None
            if production_year_element:
                try:
                    production_year = int(production_year_element[0].strip())
                    LogDebug('Production year found: %s' % production_year)
                except ValueError:
                    LogDebug('Production year is not a valid integer')
            else:
                LogDebug('No production year found.')
                production_year = None

            if release_date:
                if production_year and preference['useproductiondate'] and production_year < release_date.year:
                    metadata.originally_available_at = datetime.datetime(production_year, 1, 1)
                    LogDebug('Setting originally available at to production year: %s' % metadata.originally_available_at)
                else:
                    metadata.originally_available_at = release_date
                    metadata.year = metadata.originally_available_at.year
                    LogDebug('Setting originally available at to release date: %s' % metadata.originally_available_at)
            else:
                LogDebug('No valid release date available to set as originally available.')
        except Exception as e:
            LogDebug('Failed to update release date and year: {}'.format(str(e)))

    def update_year(self, metadata, info_page):
        try:
            production_year_element = info_page.xpath("//li[small[text()='Production Year:']]/small/following-sibling::text()")
            if production_year_element:
                production_year = int(production_year_element[0].strip())
                metadata.year = production_year
                LogDebug('Production Year Set: %s' % metadata.year)
            else:
                LogDebug('No Production Year elements found.')
        except Exception as e:
            LogDebug('Exception while parsing production year: %s' % str(e))
    

    def update_posters(self, metadata, info_page):
        try:
            img_elements = info_page.xpath("//link[@rel='image_src']/@href")
            if img_elements:
                thumb_url = img_elements[0]
                thumb = HTTP.Request(thumb_url)
                metadata.posters[thumb_url] = Proxy.Preview(thumb.content)
                LogDebug('Poster Updated with URL: %s' % thumb_url)
            else:
                LogDebug('No Poster elements found.')
        except Exception as e:
            LogDebug('Exception while setting poster: %s' % str(e))

    def update_cast(self, metadata, info_page):
        try:
            metadata.roles.clear()
            cast_elements = info_page.xpath('//div[@class="hover-popover-detail"]/img')
            for element in cast_elements:
                actor_name = element.get('title')
                actor_photo_url = element.get('src').replace("h.jpg", ".jpg")
                if actor_name:
                    role = metadata.roles.new()
                    role.name = actor_name
                    role.photo = actor_photo_url
                    LogDebug('Added Cast Member: %s' % actor_name)
        except Exception as e:
            LogDebug('Exception while updating cast: %s' % str(e))

    def update_director(self, metadata, info_page):
        try:
            metadata.directors.clear()
            director_elements = info_page.xpath('//a[contains(@label, "Director - details")]/text()')
            for director_name in director_elements:
                if director_name:
                    director = metadata.directors.new()
                    director.name = director_name.strip()
                    LogDebug('Added Director: %s' % director_name.strip())
        except Exception as e:
            LogDebug('Exception while updating director: %s' % str(e))

    def update_genres(self, metadata, info_page):
        try:
            metadata.genres.clear()
            genre_elements = info_page.xpath('//ul[@class="list-unstyled m-b-2"]//a[@label="Category"]/text()')
            for genre in genre_elements:
                genre = genre.strip()
                if genre and genre.lower() not in [x.lower() for x in preference['ignoregenres'].split('|')]:
                    metadata.genres.add(genre)
                    LogDebug('Added Genre: %s' % genre)
        except Exception as e:
            LogDebug('Exception while updating genres: %s' % str(e))

    def update_rating(self, metadata, info_page):
        try:
            rating_elements = info_page.xpath('//span[@class="rating-stars-avg"]/text()')
            if rating_elements:
                rating = float(rating_elements[0].strip()) * 2
                metadata.rating = rating
                LogDebug('Updated Rating to: %s' % rating)
            else:
                metadata.rating = None
                LogDebug('No rating found.')
        except Exception as e:
            LogDebug('Exception while updating rating: %s' % str(e))