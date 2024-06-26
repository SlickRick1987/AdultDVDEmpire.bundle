Adult DVD Empire Metadata Agent for Plex

This metadata agent is tailored for Plex Media Server and designed to fetch and apply metadata for adult film titles from the Adult DVD Empire website. It is compatible with Python 2.7, adhering to the nuances of Plex's framework for HTTP requests, XML and HTML parsing, and metadata structure.
Key Features

    Utilizes built-in Plex libraries such as HTTP, HTML, and Util.
    Designed to operate within the Python 2.7 environment, avoiding unsupported modern Python features.
    Broad exception handling caters to Plex's limited error logging capabilities.
    Detailed debug logging for easier troubleshooting.

Configuration

Before deploying the agent, make sure to adjust the Preferences within Plex to fit your setup:

    Debug Mode: Toggle detailed logging.
    Search Type: Default search parameter adjustment.
    Good Score Threshold: Configure the minimum score for accepting search results automatically.

Usage

The agent automatically triggers searches and updates metadata when movies are added to your Plex 
library. The agent expects movies to be named in proper Plex movie format i.e. Title (Year).ext.  
The agent behavior can be adjusted by adding specific tags to movie titles:

    {ade-1234567}: Directly queries Adult DVD Empire using a specific ID provided in the tag.
    
    {tmdb-123456} and {imdb-tt1234567}: These tags prevent the agent from performing any searches 
    or updates, allowing manual matching or deferment to other agents specifically designed for TMDB 
    or IMDB, respectively. This is useful for titles where more accurate or specific metadata is needed 
    that the primary agent may not handle well.


Installation

    Download the agent bundle.
    Place it in the Plex Plug-ins directory.
    Restart Plex Media Server.
    Configure the agent via Plex's server settings under Agents.

Modifications

Please ensure any modifications to the code maintain compatibility with Python 2.7 
and do not introduce features that are unsupported in the restricted Plex plugin environment. 
This ensures stability and compatibility across different server setups.

Example

To activate specific functionalities, rename your movie files like so:

Examples of proper naming for the agent is in the Plex style, 
    
    Title (Year). 

    The Cat's Meow (2010).mp4
    Batman VS Superman (2023).mp4
    Spider-Man XXX 2: An Axel Braun Parody (2014).mp4
    
    If using these triggers:
    
    Title (Year) {tag}
   
    The Cat's Meow (2010) {ade-1528431}.mp4
    Batman VS Superman (2023) {tmdb-1203062}.mp4
    Spider-Man XXX 2: An Axel Braun Parody (2014) {imdb-tt3798010}.mp4


This metadata agent provides flexible options for handling metadata, either by direct 
fetching from Adult DVD Empire or by deferring to specialized agents, ensuring your 
library remains up-to-date and accurately represented.

Troubleshooting

    Metadata not fetching:
        Ensure movie titles are named correctly.
        Check the Plex logs for any specific errors returned by the agent.
        There is extensive logging, so turn on the debugger and have a look at the logs.
    Plugin not loading:
        Confirm the plugin is placed in the correct directory and that Plex Media Server was restarted after installation.

Logging

    To view detailed logs for troubleshooting, ensure debug logging is enabled in the 
    Plex server settings and review the logs typically located at:
        Windows: C:\Users\[Your Username]\AppData\Local\Plex Media Server\Logs
        macOS and Linux: ~/Library/Logs/Plex Media Server/

Contributions

Contributions to improve the agent or address bugs are welcome via GitHub pull requests.  
The discussion board is active and you can notify if things are not working.

Thank You

This is largely a complete re-write of several older Plex Agent projects.  Many thanks to all who have come before.
And a special thanks to ChatGPT3.5 for helping to brute force figure out how to code this project!
