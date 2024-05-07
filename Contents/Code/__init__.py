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
Date: May 6, 2024
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
        Log('[DEBUG] {0}'.format(message))

LogDebug('Agent debug logging is enabled!' if DEBUG else 'Agent debug logging is disabled!')
studioascollection = preference['studioascollection']
searchtype = preference['searchtype'] if preference['searchtype'] != 'all' else 'allsearch'
LogDebug('Search Type: {0}'.format(searchtype))

GOOD_SCORE = max(int(preference['goodscore'].strip()), 1)
LogDebug('Good Score Threshold: {0}'.format(GOOD_SCORE))
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
        # Initial Logging to understand what's received
        LogDebug('Received search query (media.name): {0}'.format(media.name))
        LogDebug('Received search query (media.title): {0}'.format(media.title))
        LogDebug('Received filename: {0}'.format(media.filename))

        # Decoding the filename to work with it
        decoded_filename = urllib2.unquote(media.filename)  # Ensure this is done before any usage
        LogDebug('Decoded filename: {0}'.format(decoded_filename))

        # Check if this might be a manual search by comparing media.name and media.title
        if media.name and media.name != media.title:
            # Manual entry likely, use media.name
            search_query = media.name
            LogDebug('Manual search detected, using media.name: {0}' .format(search_query))
        else:
            # Automatic or no specific search handling
            # Proceed with operations on decoded_filename or handle other scenarios
            pass

        # Consolidated Regex for special tags and title/year extraction
        special_tag_pattern = r'{(tmdb-\d+|imdb-tt\d+|ade-(\d+))}'
        title_year_pattern = r'[^\\]*\\([^\\]+) \((\d{4})\)(?: - ?(?:cd|disc|disk|dvd|part|pt)\d+)?(?: \{[^}]*\})?\.([^.]+)$'
        title, year, special_id = None, None, None  # Initialize 'title' and 'year' here

        # Searching for special tags
        special_tags = re.findall(special_tag_pattern, decoded_filename)
        special_id = None

        for tag in special_tags:
            LogDebug('Found special tag: {0}'.format(tag[0]))  # Using index 0 if tag is a tuple
            if 'tmdb' in tag[0] or 'imdb' in tag[0]:
                LogDebug('TMDB or IMDB tag found, skipping search.')
                return
            elif 'ade-' in tag[0]:
                # Extract just the numeric part after 'ade-'
                ade_id_match = re.search(r'ade-(\d+)', tag[0])
                if ade_id_match:
                    special_id = ade_id_match.group(1)
                    LogDebug('Special ADE ID found: {0}'.format(special_id))

        # Attempt to extract title and year from filename
        match = re.search(title_year_pattern, decoded_filename)
        if match:
            title, year, ext = match.groups()
            title = title.strip()  # Clean up any leading/trailing whitespace
            LogDebug('Extracted title: {0}, year: {1}, extension: {2}'.format(title, year, ext))          
        else:
            # Fallback to media.name and media.year if regex fails
            title = media.name if media.name else media.title
            year = media.year if media.year else None
            LogDebug('Using fallback title: {0}, year: {1}'.format(title, year))


        # Use the determined 'title' for further processing
        LogDebug('Received search query: {0}'.format(title))

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
            LogDebug('Found {0} movies on the search page.'.format(len(movies)))
            if not movies:
                LogDebug('No movies found on the search page.')
                return

            for movie in movies:
                title_element = movie.xpath('.//a[contains(@label,"Title")]')
                if title_element:
                    movie_title = title_element[0].text_content().strip()
                else: 
                    LogDebug('Movie title element not found')
                    continue  # Skip to the next movie if the title element is missing

                LogDebug('Processing movie: {0}'.format(movie_title))

                # Adjust title format if it ends with ', The'
                if movie_title.endswith(', The'):
                    movie_title = 'The ' + movie_title[:-5]
                    LogDebug('Adjusted movie title: {0}'.format(movie_title))
                
                href_element = title_element[0].get('href')
                if href_element:
                    movie_id = href_element.split('/', 2)[1]
                    LogDebug('Movie ID: {0}'.format(movie_id))
                else:
                    LogDebug('No href found for movie: {0}'.format(movie_title))
                    continue

                dvd_elements = movie.xpath('.//a[@title="DVD" or @title="dvd"]')
                movie_format = 'DVD' if dvd_elements else 'VOD'
                LogDebug('Movie format: {0}'.format(movie_format))
                
                # Extract year
                year_element = movie.xpath('.//small[contains(text(),"released")]/following-sibling::text()')
                cur_year = 9999  # Default year if not found
                if year_element:
                    year_element_text = year_element[0].strip()
                    year_match = re.search(r'\d{2}/\d{2}/(\d{4})', year_element_text)
                    if year_match:
                        cur_year = int(year_match.group(1))
                        LogDebug('Movie year found: {0}'.format(cur_year))
                    else:
                        LogDebug('No year match found for text: {0}'.format(year_element_text))
                else:
                    LogDebug('Year element not found for movie: {0}'.format(movie_title))                

                score = INITIAL_SCORE - Util.LevenshteinDistance(title.lower(), movie_title.lower())
                LogDebug('Raw Score for movie: {0}'.format (score))
                # Check if years match, and apply a penalty if they do not

                if year and cur_year:
                   year = int(year)
                   cur_year = int(cur_year)
                LogDebug('Comparing years - Extracted Year: {0}, Movie Year: {1}'.format(year, cur_year))

                if year and cur_year:
                    if year != cur_year:
                        year_penalty = 10
                        score = score - year_penalty
                        LogDebug('Year penalty applied for movie: {0}; Penalty: -{1}, New Score: {2}'.format(movie_title, year_penalty, score))
                    else:
                        LogDebug('Years match, no penalty applied. Year: {0}, Movie Year: {1}'.format(year, cur_year))
                else:
                    LogDebug('One of the year values is None. Year: {0}, Movie Year: {1}'.format(year, cur_year))
                 
                if special_id and movie_id == special_id:
                    movie_dict.clear()  # Clearing all previous entries if special ID matches
                    movie_dict[(movie_title, cur_year)] = [(movie_id, movie_format, 100)]
                    break  # Stop further processing as we found the match
                else:
                    if (movie_title, cur_year) not in movie_dict:
                        movie_dict[(movie_title, cur_year)] = []
                    movie_dict[(movie_title, cur_year)].append((movie_id, movie_format, score))

                LogDebug('Score for movie: {0} is {1}'.format(movie_title, score))

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
                            LogDebug('Adjusted VOD score for {0}: {1}'.format(key[0], score // 2))


            # Append results to Plex based on GOOD_SCORE threshold
            good_results_exist = False

            # First pass to check if any good results exist
            for key, movie_info in movie_dict.items():
                for id, format, score in movie_info:
                    if score >= GOOD_SCORE:       
                        good_results_exist = True
                        break
                if good_results_exist:
                     break            

            # Second pass to append results based on the existence of good results
            for key, movie_info in movie_dict.items():
                for id, format, score in movie_info:
                    title_with_year = "{} ({})".format(key[0], key[1]) if key[1] else key[0]  # Append year if available
                    # Check if any good results exist, append only those; else append all
                    if good_results_exist:
                        if score >= GOOD_SCORE:
                            results.Append(MetadataSearchResult(id=id, name=title_with_year, score=score, lang=lang))
                    else:
                        results.Append(MetadataSearchResult(id=id, name=title_with_year, score=score, lang=lang))

            
            results.Sort('score', descending=True)
            LogDebug('Results processed and appended based on score threshold.')

        except urllib2.HTTPError as e:
            LogDebug('HTTP Error: {0} - {1}'.format(e.code, search_url))
        except urllib2.URLError as e:
            LogDebug('URL Error: {0} - {1}'.format(e.reason, search_url))
        except Exception as e:
            LogDebug('Failed to fetch or parse search results: {0}'.format(str(e)))

    def update(self, metadata, media, lang):
        LogDebug('Starting metadata update for ID: {0}'.format(metadata.id))
        info_url = ADE_MOVIE_INFO % metadata.id
        LogDebug('Constructed movie info URL: {0}'.format(info_url))

        
        try:
            info_page = HTML.ElementFromURL(info_url)
            LogDebug('Movie info page retrieved.')

            # Update movie title from the title from the media information
            import re
            title_without_year = re.sub(r"\s*\(\d{4}\)\s*$", "", media.title)  # Regex to remove year from the end
            metadata.title = title_without_year
            LogDebug('Updated movie title: {0}'.format(metadata.title))

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

            # Pulling screenshots if enabled
            if Prefs['pullscreens']:
                self.retrieve_screenshots(metadata, info_page)

            # Pulling gallery images if available and enabled
            if Prefs['pullgallery']:
                self.retrieve_gallery_images(metadata, info_url)

            # Update collections
            if Prefs['studioascollection'] and metadata.studio:
                self.update_collections(metadata, info_page, metadata.studio)

            # Additional metadata fields can be updated here...
            
        except urllib2.HTTPError as e:
            LogDebug('HTTP Error: {0} - {1}'.format(e.code, search_url))
        except urllib2.URLError as e:
            LogDebug('URL Error: {0} - {1}'.format(e.reason, search_url))
        except Exception as e:
            LogDebug('Failed to update metadata: {0}'.format(str(e)))

    def update_tagline(self, metadata, info_page):
        try:
            tagline_element = info_page.xpath('//h2[contains(@class, "test")]/text()')
            if tagline_element:
                tagline = tagline_element[0].strip()
                metadata.tagline = tagline
                LogDebug('Tagline Found and Set: {0}'.format(metadata.tagline))
            else:
                LogDebug('No tagline element found.')
        except Exception as e:
            LogDebug('Exception while parsing tagline: {0}'.format(str(e)))

    def update_summary(self, metadata, info_page):
        try:
            summary_elements = info_page.xpath('//div[@class="synopsis-content"]/p')
            if summary_elements:
                summary = summary_elements[0].text_content().strip()
                metadata.summary = summary
                LogDebug('Summary Found and Set: {0}'.format(summary))
            else:
                LogDebug('No summary elements found.')
        except Exception as e:
            LogDebug('Exception while parsing summary: {0}'.format(str(e)))

    def update_content_rating(self, metadata, info_page):
        try:
            # Extract content rating
            rating_element = info_page.xpath("//li[small[text()='Rating: ']]/small/following-sibling::text()")
            if rating_element:
                metadata.content_rating = rating_element[0].strip()
                LogDebug('Content Rating Found: {0}'.format(metadata.content_rating))
            else:
                LogDebug('No Content Rating elements found.')
        except Exception as e:
            LogDebug('Exception while parsing content rating: {0}'.format(str(e)))
    
    def update_studio(self, metadata, info_page):
        try:
            studio_element = info_page.xpath("//li[small[text()='Studio: ']]/small/following-sibling::a/text()")
            if studio_element:
                metadata.studio = studio_element[0].strip()
                LogDebug('Studio Found: {0}'.format(metadata.studio))
            else:
                LogDebug('No Studio elements found.')
        except Exception as e:
            LogDebug('Exception while parsing studio: {0}'.format(str(e)))
    
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
                    LogDebug('Release date parsed successfully: {0}'.format(release_date.strftime('%Y-%m-%d')))

                else:
                    LogDebug('Failed to parse release date: {0}'.format(release_date_str))
                

            Production_year = None
            if production_year_element:
                try:
                    production_year = int(production_year_element[0].strip())
                    LogDebug('Production year found: {0}'.format(production_year))
                except ValueError:
                    LogDebug('Production year is not a valid integer')
            else:
                LogDebug('No production year found.')
                production_year = None

            if release_date:
                if production_year and preference['useproductiondate'] and production_year < release_date.year:
                    metadata.originally_available_at = datetime.datetime(production_year, 1, 1)
                    LogDebug('Setting originally available at to production year: {0}'.format(metadata.originally_available_at))
                else:
                    metadata.originally_available_at = release_date
                    metadata.year = metadata.originally_available_at.year
                    LogDebug('Setting originally available at to release date: {0}'.format(metadata.originally_available_at))
            else:
                LogDebug('No valid release date available to set as originally available.')
        except Exception as e:
            LogDebug('Failed to update release date and year: {0}'.format(str(e)))

    def update_year(self, metadata, info_page):
        try:
            production_year_element = info_page.xpath("//li[small[text()='Production Year:']]/small/following-sibling::text()")
            if production_year_element:
                production_year = int(production_year_element[0].strip())
                metadata.year = production_year
                LogDebug('Production Year Set: {0}'.format(metadata.year))
            else:
                LogDebug('No Production Year elements found.')
        except Exception as e:
            LogDebug('Exception while parsing production year: {0}'.format(str(e)))
    

    def update_posters(self, metadata, info_page):
        try:
            img_elements = info_page.xpath("//link[@rel='image_src']/@href")
            if img_elements:
                thumb_url = img_elements[0]
                thumb = HTTP.Request(thumb_url)
                metadata.posters[thumb_url] = Proxy.Preview(thumb.content)
                LogDebug('Poster Updated with URL: {0}'.format(thumb_url))
            else:
                LogDebug('No Poster elements found.')
        except Exception as e:
            LogDebug('Exception while setting poster: {0}'.format(str(e)))

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
                    LogDebug('Added Cast Member: {0}'.format(actor_name))
        except Exception as e:
            LogDebug('Exception while updating cast: {0}'.format(str(e)))

    def update_director(self, metadata, info_page):
        try:
            metadata.directors.clear()
            director_elements = info_page.xpath('//a[contains(@label, "Director - details")]/text()')
            for director_name in director_elements:
                if director_name:
                    director = metadata.directors.new()
                    director.name = director_name.strip()
                    LogDebug('Added Director: {0}'.format(director_name.strip()))
        except Exception as e:
            LogDebug('Exception while updating director: {0}'.format(str(e)))

    def update_genres(self, metadata, info_page):
        try:
            metadata.genres.clear()
            genre_elements = info_page.xpath('//ul[@class="list-unstyled m-b-2"]//a[@label="Category"]/text()')
            for genre in genre_elements:
                genre = genre.strip()
                if genre and genre.lower() not in [x.lower() for x in preference['ignoregenres'].split('|')]:
                    metadata.genres.add(genre)
                    LogDebug('Added Genre: {0}'.format(genre))
        except Exception as e:
            LogDebug('Exception while updating genres: {0}'.format(str(e)))

    def update_rating(self, metadata, info_page):
        try:
            rating_elements = info_page.xpath('//span[@class="rating-stars-avg"]/text()')
            if rating_elements:
                rating = float(rating_elements[0].strip()) * 2
                metadata.rating = rating
                LogDebug('Updated Rating to: {0}'.format(rating))
            else:
                metadata.rating = None
                LogDebug('No rating found.')
        except Exception as e:
            LogDebug('Exception while updating rating: {0}'.format(str(e)))

    def retrieve_screenshots(self, metadata, info_page):
        try:
            imgs = info_page.xpath('//a[contains(@rel, "scenescreenshots")]')
            pullscreenscount = int(Prefs['pullscreenscount'])
            if imgs and pullscreenscount > 0:
                selected_imgs = random.sample(imgs, min(pullscreenscount, len(imgs)))
                for img in selected_imgs:
                    thumb_url = img.attrib['href']
                    thumb = HTTP.Request(thumb_url)
                    metadata.art[thumb_url] = Proxy.Media(thumb)
                    LogDebug('Added screenshot: {0}'.format(thumb_url))
        except Exception as e:
            LogDebug('Exception while retrieving screenshots: {0}'.format(str(e)))

    def retrieve_gallery_images(self, metadata, base_url):
        try:
            gallery = HTML.ElementFromURL(base_url + '/gallery')
            imgs = gallery.xpath('//div/a[contains(@class, "thumb fancy")]')
            pullgallerycount = int(Prefs['pullgallerycount'])
            if imgs and pullgallerycount > 0:
                selected_imgs = random.sample(imgs, min(pullgallerycount, len(imgs)))
                for img in selected_imgs:
                    image_url = img.attrib['href']
                    image = HTTP.Request(image_url)
                    metadata.art[image_url] = Proxy.Media(image)
                    LogDebug('Added gallery image: {0}'.format(image_url))
        except Exception as e:
            LogDebug('Exception while retrieving gallery images: {0}'.format(str(e)))

    def update_collections(self, metadata, html, studio):
        try:
            metadata.collections.clear()  # Clears existing collections to avoid duplicates

            # Handle Series as Collection
            series_links = html.xpath('//a[contains(@label, "Series")]')
            if series_links:
                series = HTML.StringFromElement(series_links[0])  # Assuming the first link is the correct one
                series_name = HTML.ElementFromString(series).text_content().strip()
                series_name = series_name.split('"')[1]  # Parsing might vary based on actual HTML structure
                metadata.collections.add(series_name)
                LogDebug('Added Series to collections: {0}'.format(series_name))

            # Handle Studio as Collection based on Preference
            if Prefs['studioascollection'] and studio:
                metadata.collections.add(studio)
                LogDebug('Added Studio to collections as per user preference: {0}'.format(studio))

        except Exception as e:
            LogDebug('Exception while updating collections: {0}'.format(str(e)))
