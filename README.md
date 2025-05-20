# Bring-a-Trailer-Scraper
A collection of Utilities to Scrape Auction Data from Bring a Trailer, Sample Vehicle is the 2015-2020 Mustang GT-350

Python Code, Selenium and Chromium scraper, and error checking plus progress

Writes to InfluxDB, this project is on a Raspberry Pi but of course portable. Grafana visualizations

The file you want is bat_historical_selenium_scraper.py
I never had much luck with the RSS one (too few listings to bother), and also the influx_writer.py

Includes grafana starter panel showing all the GT-350s by sales price and sale date as a .json to import
