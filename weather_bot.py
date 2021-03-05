#weather bot example

#if you don't whish to set this
#just copy the file to the top-level
#folder and run it there w/out this
import os
import sys
sys.path.append("/app/.heroku/python/lib/python3.7/site-packages")
sys.path.append(".")
sys.path.append("/app/dokkaebi")
sys.path.append("dokkaebi")
print(sys.path)
print(os.environ.get('PORT', 5000))

from enum import Enum

import string
import datetime
from datetime import date
from timezonefinder import TimezoneFinder
from pytz import timezone
import urllib.parse
import dominate
from dominate.tags import *
from dominate.util import raw
from dominate.util import text

import requests
import json
import cherrypy
import plotly.graph_objects
import plotly.offline
from dokkaebi import dokkaebi
from configparser import ConfigParser

#appending to sys.path allows
#config to be read relative to that path
#even though this file is in the examples folder
config = ConfigParser()
config.read('weather_bot.ini')

#be sure to cast anything that shouldn't
#be a string - reading the .ini file
#seems to result in strings for every item read.
hook_data = {
	'hostname': config["Telegram"]["HOSTNAME"], 
	#'port': int(os.environ.get("PORT")), 
	'port': int(config["Telegram"]["PORT"]),
	'token': config["Telegram"]["BOT_TOKEN"], 
	'url': config["Telegram"]["WEBHOOK_URL"],
	'environment': config["Telegram"]["ENVIRONMENT"]
}

#you can actually store more data
#in your bot command payload
#here, i put an example in with
#each command to illustrate its use
#keep in mind that Telegram will drop
#the extra fields when it stores it, so use
#this copy of the data for example storeage/retrieval
bot_commands = {
	"commands": [
		{'command': 'start', 'description': 'starts the bot.', 'example': "Just issue /start in the Telegram message box."},
		{'command': 'cityweather', 'description': 'Get the current weather information of any city in the world available through OpenWeatherMap.org.', 'example': "\nThe command: /cityweather San Diego will return weather information for San Diego.\nSpecifying the command with city, state, and/or country as\n/cityweather San Diego, Ca, US\nwill also work as will\n/cityweather Paris, Fr\nTry copying and pasting one of these commands to get a feel for it. Enjoy the weather! &#128516;"},
		{'command': 'zipweather', 'description': 'Get the current weather information of any zip code in the USA and many postal codes throughout the world available through OpenWeatherMap.org.', 'example': "\nThe command: /zipweather 92113 will return weather information for the San Diego 92113 zip code.\n/zipweather WC2N 5DU, GB will return weather information from London, GB.\nTry copying and pasting one of these commands to get a feel for it. Enjoy the weather! &#128516;"},
		{'command': 'dash', 'description': 'Get the current weather information and forecast of any city in the world available through OpenWeatherMap.org as a nice dashboard.', 'example': "\nThe command: /dash San Diego will return a link to a weather dashboard for San Diego.\nSpecifying the command with city, state, and/or country as\n/dash San Diego, Ca, US\nwill also work as will\n/dash Paris, Fr\nTry copying and pasting one of these commands to try it out."}
	]
}

#you'll need your own API key
#at api.openweathermap.org
openweather = {
	'key': config["OpenWeather"]["API_KEY"]
}

#you'll also need a mapbox account
#for generating a map with the coordinates
#from openweathermap
mapbox = {
	'key': config["Mapbox"]["API_KEY"]
}

#bitly access
bitly = {
	"token": config["Bitly"]["TOKEN"]
}

class WeatherType(Enum):
	CITY = 0
	POSTAL_CODE = 1
	CITY_DASH = 2

states = {
	"AL", "AK", "AR", "AZ", "CA", "CO", "CT", "DE", "FL", "GA",
	"HI", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD",
	"ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH",
	"NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI", "SC",
	"SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
}

class Bot(dokkaebi.Dokkaebi):
	@cherrypy.expose
	def dash(self, **params):
		#get the current weather first...
		current = {}
		
		#then rest...
		dash_data = {}
		if "city" in params:
			if "country_code" in params:
				if "state" in params:
					self.cityDash({"city": params["city"], "state": params["state"], "country_code": params["country_code"]}, dash_data)
					c = self.parseCommandAndParams("/cityweather " + params["city"] + "," + params["state"] + "," + params["country_code"])
					#print("city parsed: {}".format(c))
					self.prepareData(WeatherType.CITY, c["user_parameters"], current)
				else:
					self.cityDash({"city": params["city"], "country_code": params["country_code"]}, dash_data)
					c = self.parseCommandAndParams("/cityweather " + params["city"] + "," + params["country_code"])
					#print("city parsed: {}".format(c))
					self.prepareData(WeatherType.CITY, c["user_parameters"], current)
			else:
				self.cityDash({"city": params["city"]}, dash_data)
				c = self.parseCommandAndParams("/cityweather " + params["city"])
				#print("city parsed: {}".format(c))
				self.prepareData(WeatherType.CITY, c["user_parameters"], current)
		else:
			return "Bad parameters - need a city name for a forecast dashboard at a minimum."
		
		#print(dash_data)
		#print(current)

		#set up the doc
		doc = dominate.document(title="Weather Dashboard")

		with doc.head:
			script(type='text/javascript', src="https://cdn.plot.ly/plotly-latest.min.js")
			script(type='text/javascript', src="https://cdnjs.cloudflare.com/ajax/libs/animejs/3.2.0/anime.min.js")
			script(type='text/javascript', src="https://code.jquery.com/jquery-3.5.1.min.js")
			script(type='text/javascript', src="https://cdn.jsdelivr.net/npm/popper.js@1.16.1/dist/umd/popper.min.js", integrity="sha384-9/reFTGAW83EW2RDu2S0VKaIzap3H66lZH81PoYlFhbGU+6BZp6G7niu735Sk7lN", crossorigin="anonymous")
			script(type='text/javascript', src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js", integrity="sha384-B4gt1jrGC7Jh4AgTPSdUtOBvfO8shuf57BaghqFfPlYxofvL8/KUEfYiJOMMV+rV", crossorigin="anonymous")
			script(type='text/javascript', src="https://cdn.datatables.net/v/bs4/dt-1.10.22/datatables.min.js")
			script(type='text/javascript', src="https://api.mapbox.com/mapbox-gl-js/v2.0.0/mapbox-gl.js")
			link(rel='stylesheet', href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css", integrity="sha384-JcKb8q3iqJ61gNV9KGb8thSsNjpSL0n8PARn9HuZOnIxN0hoP+VmmDGMN5t9UJ0Z", crossorigin="anonymous")
			link(rel='stylesheet', href="https://cdn.datatables.net/v/bs4/dt-1.10.22/datatables.min.css")
			link(rel='stylesheet', href="/static/css/styles.css")
			link(rel='stylesheet', href="https://api.mapbox.com/mapbox-gl-js/v2.0.0/mapbox-gl.css")
			link(rel='stylesheet', href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css")
			script(type='text/javascript', src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js")

		#handle display under error conditions...
		if dash_data == None or dash_data == {}:
			with doc:
				wrap = div(id="content", cls="container-fluid")
				with wrap:
					div(raw("Unable to create a dashboard from the parameters given!<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\"><span aria-hidden=\"true\">&times;</span></button>"), cls="msg alert alert-danger alert-dismissible fade show", role="alert")
					div(h1("Please take a closer look at your command and try again :("))
					
			return doc.render()

		dy = []
		dates = []
		mins = []
		maxes = []
		for i in range(0, len(dash_data["forecasts"])):
			dy.append(dash_data["forecasts"][i]["temp"])
			mins.append(dash_data["forecasts"][i]["min_temp"])
			maxes.append(dash_data["forecasts"][i]["max_temp"])
			dates.append(dash_data["forecasts"][i]["date_time"])

		miny = min(mins)
		maxy = max(maxes)

		fig = plotly.graph_objects.Figure(
		    layout_title_text="Hourly Forecast"
		)
		fig.add_trace(
			plotly.graph_objects.Scatter(
				x=dates, 
				y=dy, 
				fill='tozeroy', 
				line=dict(color='#990000', width=4), 
				mode='lines+markers+text', 
				name='Temp',
				marker=dict(size=14)
			)
		)
		#fig.add_trace(plotly.graph_objects.Scatter(x=dx, y=maxes, name='High', line=dict(color='firebrick', width=16)))
		#fig.add_trace(plotly.graph_objects.Scatter(x=dx, y=mins, name='Low', line=dict(color='royalblue', width=4)))

		#fig.update_layout(yaxis=dict(range=[miny, maxy]))
		fig.update_layout(xaxis_range=[dates[0], dates[7]], yaxis_title="Temperature (degrees F)", xaxis_title="Date and Time (24-hour clock format)", template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
		#fig.update_yaxes(nticks=5)
		#fig.update_xaxes(nticks=5)
		fig.update_xaxes(showgrid=False)
		fig.update_yaxes(showgrid=False)
		
		line_chart = plotly.io.to_html(fig, include_plotlyjs=False, full_html=False)

		share_url = hook_data["url"] + "/dash?" + urllib.parse.urlencode(params)
		#print(share_url)
		share_comment = "Forecast dashboard: " + dash_data["place"]
		#print(share_comment)
		with doc:
			wrap = div(id="content", cls="container-fluid")
			with wrap:
				div(raw("{} - Dashboard created successfully!<button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\"><span aria-hidden=\"true\">&times;</span></button>".format(dash_data["place"])), cls="msg alert alert-info alert-dismissible fade show", role="alert")
				div(
					script(
						src="https://telegram.org/js/telegram-widget.js?11", 
						data_telegram_share_url=share_url, 
						data_comment=share_comment, 
						data_size="large"
					),
					cls="row justify-content-center",
					style="margin: 10px; width: 100%;"
				)
				with div(cls="row justify-content-center"):
					with div(cls="col-6"):
						div(
						p(dash_data["timestamp"].strftime("%I:%M%p %Z %b. %d"), cls="current-date"),
						h1(dash_data["place"]),
						h2(raw("{}°F".format(current["temp"]) + "&nbsp;<img src=\"" + "https://openweathermap.org/img/wn/" + current["icon"] + "@2x.png\"" + ">")),
						p("Feels like {}°F. ".format(current["feel"]) + current["main"] + ". " + current["desc"]),
						blockquote(
							p("Air pressure - {}hPa".format(current["pressure"])),
							p("Humidity - {}%".format(current["humidity"]))
						)
					)
					with div(cls="col-6"):
						div(id="map")
				with div(cls="row justify-content-center"):
					with div(cls="col-6"):
						div(raw(line_chart), id="line-chart")
					with div(cls="col-6"):
						h2("5-Day Forecast")
						dt = table(id="forecast", cls="table table-dark table-borderless table-hover")
						with dt:
							with tbody():
								for i in range(0, len(dash_data["forecasts"])):
									date = dash_data["forecasts"][i]["date_time"].strftime("%a. %b %d, %Y")
									if i == 0 or i%8 == 0:
										with tr():
											td(date)
											td("{}".format(dash_data["forecasts"][i]["temp"]) + "°F")
											td(raw(dash_data["forecasts"][i]["main"] + "/" + dash_data["forecasts"][i]["description"] + "&nbsp;<img src=\"" + "https://openweathermap.org/img/wn/" + dash_data["forecasts"][i]["icon"] + ".png\"" + ">"))
			
			script().add("$(document).ready(function() { $('#forecast').DataTable();} );")
			script().add("var mymap = L.map('map').setView([{},".format(dash_data["latitude"]) + "{}".format(dash_data["longitude"]) + "], 13);"
				+ "var marker = L.marker([{},".format(dash_data["latitude"]) + "{}".format(dash_data["longitude"]) + "]).addTo(mymap);"
			)
			script().add("var link = new DOMParser().parseFromString('Map data © <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors, Imagery © <a href=\"https://www.mapbox.com/\">Mapbox</a>', 'text/html').documentElement.textContent;"
				+ "L.tileLayer('https://api.mapbox.com/styles/v1/{{id}}/tiles/{{z}}/{{x}}/{{y}}?access_token={}'".format(mapbox["key"])
				+ ", { maxZoom: 18, "
				+ "attribution: link, "
				+ "id: 'mapbox/streets-v11', "
				+ "tileSize: 512, "
				+ "zoomOffset: -1, "
				+ "accessToken: '" + mapbox["key"] +"'"
				+ "}).addTo(mymap);")
			script().add("$('.msg').fadeTo(2000, 500).slideUp(500, function(){ $('.msg').slideUp(500);});")

		return doc.render()

	def prepareData(self, type, user_parameters, data):
		if type == WeatherType.CITY:
			self.weatherByCity(user_parameters, data)
		elif type == WeatherType.POSTAL_CODE:
			self.weatherByPostalCode(user_parameters, data)
		elif type == WeatherType.CITY_DASH:
			self.cityDash(user_parameters, data)

	def prepareCityForecast(self, res, data):
		if res != {}:
			tf = TimezoneFinder()
			#print(res)
			if res.get("list") and res["list"] != None:
				#print("there is a list of forecasts")
				forecasts = []
				for i in range(0, len(res["list"])):
					forecast = {
						"temp": res["list"][i]["main"]["temp"],
						"feels_like": res["list"][i]["main"]["feels_like"],
						"min_temp": res["list"][i]["main"]["temp_min"],
						"max_temp": res["list"][i]["main"]["temp_max"],
						"pressure": res["list"][i]["main"]["pressure"],
						"humidity": res["list"][i]["main"]["humidity"],
						"main": res["list"][i]["weather"][0]["main"],
						"description": res["list"][i]["weather"][0]["description"],
						"icon": res["list"][i]["weather"][0]["icon"],
						"dt": res["list"][i]["dt"],
						"date_text": datetime.datetime.fromtimestamp(res["list"][i]["dt"], tz=timezone(tf.timezone_at(lng=res["city"]["coord"]["lon"], lat=res["city"]["coord"]["lat"]))).strftime("%m-%d-%Y %I:%M:%S %p %Z"),
						"date_time": datetime.datetime.fromtimestamp(res["list"][i]["dt"], tz=timezone(tf.timezone_at(lng=res["city"]["coord"]["lon"], lat=res["city"]["coord"]["lat"]))),
						"dt_txt": res["list"][i]["dt_txt"]
					}
					forecasts.append(forecast)

				data.update({"forecasts": forecasts})

			if res.get("city") and res["city"] != None:
				data.update({
					"latitude": res["city"]["coord"]["lat"],
					"longitude": res["city"]["coord"]["lon"],
					"local_timezone": timezone(tf.timezone_at(lng=res["city"]["coord"]["lon"], lat=res["city"]["coord"]["lat"])),
					"country": res["city"]["country"],
					"sunrise": datetime.datetime.fromtimestamp(res["city"]["sunrise"], tz=timezone(tf.timezone_at(lng=res["city"]["coord"]["lon"], lat=res["city"]["coord"]["lat"]))),
					"sunset": datetime.datetime.fromtimestamp(res["city"]["sunset"], tz=timezone(tf.timezone_at(lng=res["city"]["coord"]["lon"], lat=res["city"]["coord"]["lat"]))),
					"timestamp": datetime.datetime.now(tz=timezone(tf.timezone_at(lng=res["city"]["coord"]["lon"], lat=res["city"]["coord"]["lat"]))),#.strftime("%A %B %d, %Y %I:%M:%S %p %Z"),
					"name": res["city"]["name"]
				})

			#print(data)

	def prepareResponse(self, res, data):
		if res != {}:
			tf = TimezoneFinder()
			
			if res.get("coord") and res["coord"] != None:
				data.update({
					"latitude": res["coord"]["lat"],
					"longitude": res["coord"]["lon"],
					"local_timezone": timezone(tf.timezone_at(lng=res["coord"]["lon"], lat=res["coord"]["lat"]))
				})

			if res.get("main") and res["main"] != None:
				data.update({
					"temp": res["main"]["temp"],
					"feel": res["main"]["feels_like"],
					"min_temp": res["main"]["temp_min"],
					"max_temp": res["main"]["temp_max"],
					"pressure": res["main"]["pressure"],
					"humidity": res["main"]["humidity"]
				})

			if res.get("weather") and res["weather"][0] != None:
				data.update({
					"main": res["weather"][0]["main"],
					"desc": res["weather"][0]["description"],
					"icon": res["weather"][0]["icon"],
				})

			if res.get("sys") and res["sys"] != None:
				data.update({
					"country": res["sys"]["country"],
					"sunrise": datetime.datetime.fromtimestamp(res["sys"]["sunrise"], tz=timezone(tf.timezone_at(lng=res["coord"]["lon"], lat=res["coord"]["lat"]))),
					"sunset": datetime.datetime.fromtimestamp(res["sys"]["sunset"], tz=timezone(tf.timezone_at(lng=res["coord"]["lon"], lat=res["coord"]["lat"]))),
					"timestamp": datetime.datetime.now(tz=timezone(tf.timezone_at(lng=res["coord"]["lon"], lat=res["coord"]["lat"]))).strftime("%A %B %d, %Y %I:%M:%S %p %Z")
				})

			if res.get("name") and res["name"] != None:
				data.update({"name": res["name"]})

	def parseCity(self, user_parameters):
		#check how long the city name is
		#and act accordingly
		state = None #user may supply the state too
		city = None
		country_code = None

		#comma-separated parameters processing
		#city could be given along with state and country
		if len(user_parameters) == 3: #city, state, and country were given
			city = " ".join(user_parameters[:(len(user_parameters) - 2)]).strip()
			#print(city)
			state = user_parameters[len(user_parameters) - 2].strip()
			#print(state)
			country_code = user_parameters[len(user_parameters) - 1].strip()
			#print(country_code)
			
		elif len(user_parameters) == 2: #as an assumption, only the city and state/country were given
			city = " ".join(user_parameters[:(len(user_parameters) - 1)]).strip()
			#print(city)
			state = user_parameters[len(user_parameters) - 1].strip()
			#print(state)
			country_code = None #user_parameters[len(user_parameters) - 1]
			#print(country_code)

		else: #otherwise it was just a city so grab it and put it in the city string
			city = user_parameters
			#print(city)

		#remove any special characters
		city = city.translate(str.maketrans('', '', string.punctuation))
		city = city.replace("’", "")

		return {"city": city, "state": state, "country_code": country_code}

	def parsePostalCode(self, user_parameters):
		postal_code = None
		country_code = None

		#comma-separated parameters processing
		#country could be given along with postal code
		if len(user_parameters) == 2: #postal code and country were given
			postal_code = " ".join(user_parameters[:(len(user_parameters) - 1)]).strip()
			#print(postal_code)
			country_code = user_parameters[len(user_parameters) - 1].strip()
			#print(country_code)
			
		else: #otherwise it was just a postal code
			postal_code = user_parameters
			#print(postal_code)

		return {"postal_code": postal_code, "country_code": country_code}

	def cityDash(self, user_parameters, data):
		city = user_parameters["city"]

		if "state" in user_parameters:
			state = user_parameters["state"]
		else:
			state = None

		if "country_code" in user_parameters:
			country_code = user_parameters["country_code"]
		else:
			country_code = None

		if city != None:
			#openweather provides units parameter - we use imperial in the US
			#but the other option is metric, or don't pass in units and you'll get
			#a temperature in kelvin. if you do that, you can use the conversion
			#functions if/when you wish to convert (for example the user wants to see it
			#differently and you require units as a command parameter)
			if state != None and state != "None":
				if country_code != None and country_code != "None":
					#print('path 1')
					url = "https://api.openweathermap.org/data/2.5/forecast?q=" + city.title() + "," + state + "," + country_code + "&units=imperial&appid=" + openweather["key"]
				else:
					if state.upper() in states:
						url = "https://api.openweathermap.org/data/2.5/forecast?q=" + city.title() + "," + state + ",us&units=imperial&appid=" + openweather["key"]
						#print('path 2')
					else:
						url = "https://api.openweathermap.org/data/2.5/forecast?q=" + city.title() + "," + state + "&units=imperial&appid=" + openweather["key"]
						#print('path 3')
			else:
				url = "https://api.openweathermap.org/data/2.5/forecast?q=" + city.title() + "&units=imperial&appid=" + openweather["key"]
				#print('path 4')

			#print(url)

			res = requests.get(url).json()
			#print(res)

			if res != None and res.get("cod") == "200":
				if state != None and state != "None":
					data.update({
						"state": state,
						"place": res.get("city").get("name").title() + ", " + state.upper() + " - " + res.get("city").get("country")
					})
				else:
					data.update({"place": res.get("city").get("name").title() + " - " + res.get("city").get("country")})

				self.prepareCityForecast(res, data)
			else:
				print("OpenWeatherMap query failed ({}): ".format(res.get("cod")) + res.get("message"))

	def weatherByCity(self, user_parameters, data):
		params = self.parseCity(user_parameters)

		city = params["city"]
		state = params["state"]
		country_code = params["country_code"]

		if city != None:
			#openweather provides units parameter - we use imperial in the US
			#but the other option is metric, or don't pass in units and you'll get
			#a temperature in kelvin. if you do that, you can use the conversion
			#functions if/when you wish to convert (for example the user wants to see it
			#differently and you require units as a command parameter)
			if state != None:
				if country_code != None:
					#print('path 1')
					url = "https://api.openweathermap.org/data/2.5/weather?q=" + city.title() + "," + state + "," + country_code + "&units=imperial&appid=" + openweather["key"]
				else:
					if state.upper() in states:
						url = "https://api.openweathermap.org/data/2.5/weather?q=" + city.title() + "," + state + ",us&units=imperial&appid=" + openweather["key"]
						data.update({"state": state})
						#print('path 2')
					else:
						url = "https://api.openweathermap.org/data/2.5/weather?q=" + city.title() + "," + state + "&units=imperial&appid=" + openweather["key"]
						#print('path 3')
			else:
				url = "https://api.openweathermap.org/data/2.5/weather?q=" + city.title() + "&units=imperial&appid=" + openweather["key"]
				#print('path 4')

			#print(url)

			res = requests.get(url).json()
			#print(res)

			if res != None and res.get("cod") == 200:
				if state != None:
					data.update({
						"state": state,
						"place": res.get("name").title() + ", " + state.upper() + " - " + res.get("sys").get("country")
					})
				else:
					data.update({"place": res.get("name").title() + " - " + res.get("sys").get("country")})

				self.prepareResponse(res, data)
			else:
				print("OpenWeatherMap query failed ({}): ".format(res.get("cod")) + res.get("message"))

	def weatherByPostalCode(self, user_parameters, data):
		getPost = self.parsePostalCode(user_parameters)
		postal_code = getPost["postal_code"]
		country_code = getPost["country_code"]

		if postal_code != None:
			#openweather provides units parameter - we use imperial in the US
			#but the other option is metric, or don't pass in units and you'll get
			#a temperature in kelvin. if you do that, you can use the conversion
			#functions if/when you wish to convert (for example the user wants to see it
			#differently and you require units as a command parameter)
			if country_code != None:
				url = "https://api.openweathermap.org/data/2.5/weather?zip=" + postal_code + "," + country_code + "&units=imperial&appid=" + openweather["key"]
			else: #assume it's a zip in the US
				url = "https://api.openweathermap.org/data/2.5/weather?zip=" + postal_code + ",us&units=imperial&appid=" + openweather["key"]

			#print(url)

			res = requests.get(url).json()
			#print(res)

			if res != None and res.get("cod") == 200:
				data.update({"place": res.get("name").title() + " - " + res.get("sys").get("country")})
				self.prepareResponse(res, data)
			else:
				print("OpenWeatherMap query failed ({}): ".format(res.get("cod")) + res.get("message"))

	def parseCommandAndParams(self, user_parameters):
		#this will work both for single word commands
		#and commands with multiple text parameters
		command = user_parameters.split(' ')[0] #grab command keyword...
		p = ""
		if user_parameters.split(' ')[1:]:#split on spaces first...
			if "," in user_parameters:#split on commas if there...
				p = user_parameters.split(',')
				#re-establish the city name if multi-word (for example ["san", "luis", "obispo", "ca", "us"] 
				#becomes reconstituted as ["san luis obispo", "ca", "us"] as you would want it to be)
				p[0] = " ".join(p[0].split(' ')[1:])
				#print("user params: {}".format(p))
				#print(p)
			else: #no commas so its just the city
				p = " ".join(user_parameters.split(' ')[1:]) #again, could be a multi-word city...
				#print("user params: {}".format(p))
				#print(p[0])

		return {"command": command, "user_parameters": p}

	def handleData(self, data):
		#print(data)

		if "message" in data:
			if "text" in data["message"]:
				parsed = self.parseCommandAndParams(data["message"]["text"])
				command = parsed["command"]
				user_parameters = parsed["user_parameters"]
		else:
			command = None

		chat_id = data["message"]["chat"]["id"]
		user_first_name = data["message"]["from"]["first_name"]
		
		if command in ["/start", "/start@" + self.bot_info["username"]]:
			#for fun!
			weather = "https://external-content.duckduckgo.com/iu/?u=https://media.giphy.com/media/5yvoGUhBsuBwY/giphy.gif&f=1&nofb=1"
			print(self.sendAnimation({"chat_id": chat_id, "animation": weather}).json())
			msg = {
				"chat_id": chat_id,
				"text": "Thanks for using "  + self.bot_info["username"] + ", " + user_first_name + "!\n" + "It's always wise to check the weather before you run outside. " + "&#128514;",
				"parse_mode": "html"
			}
			print(self.sendMessage(msg).json())
			print(self.sendMessage({
				"chat_id": chat_id, 
				"text": "Just submit a command to get weather information.\nFor example, the command: /cityweather San Diego\nwill return weather information for San Diego.\nUse the /help command for the full list of commands."
			}).json())

		elif command in ["/help", "/help@" + self.bot_info["username"]]:
			#append the help string from
			#the bot_command data structure
			t = ""
			for x in bot_commands["commands"]:
				t += "".join("/" + x["command"] + " - " + x["description"] + "\nExample: " + x["example"]) + "\n"
			
			msg = {
				"chat_id": chat_id,
				"text": "The following commands are available: \n" + t.rstrip(),
				"parse_mode": "html"
			}
			
			#print(t.rstrip())
			print(self.sendMessage(msg).json())

		elif command in ["/dash", "/dash@" + self.bot_info["username"]]:
			city_data = self.parseCity(user_parameters)
			#print(city_data)

			d = hook_data["url"] + "/dash?" + str(urllib.parse.urlencode(city_data))
			#print(d)

			if d != None and d != "":
				print(self.sendMessage({
					"chat_id": chat_id, 
					"text": "Your dashboard has been created! Check it out - " + d
				}).json())
			else:
				print(self.sendMessage({
					"chat_id": chat_id, 
					"text": "There was an error with the city you entered. Please check the spelling and try again."
				}).json())

		elif command in ["/cityweather", "/cityweather@" + self.bot_info["username"]]:
			city_data = {}
			self.prepareData(WeatherType.CITY, user_parameters, city_data)

			#print(city_data)
			#timezones and UTC offsets are tricky...
			#but this is close enough for the intended purpose
			#see this for more info:
			#https://stackoverflow.com/questions/17733139/getting-the-correct-timezone-offset-in-python-using-local-timezone
			#and this:
			#https://en.wikipedia.org/wiki/ISO_8601
			if city_data != {}:
				print(self.sendPhoto({
					"chat_id": chat_id,
					"photo": "http://openweathermap.org/img/wn/" + city_data.get("icon") + "@4x.png", 
					"caption": "The current weather for " + city_data.get("place") + " (" + city_data.get("timestamp") + ") :" +
							"\n--------------------------------" +
							"\n" + city_data.get("main") + "/" + city_data.get("desc") + "\n<b>Temperature</b>: {}".format(city_data.get("temp")) + " °F" +
							"\n<i>Feels like</i>: {}".format(city_data.get("feel")) + " °F" +
							"\n<b>Low</b>: {}".format(city_data.get("min_temp")) + " °F" + "\n<b>High</b>: {}".format(city_data.get("max_temp")) + " °F" +
							"\n--------------------------------" +
							"\n<i>Pressure</i>: {}".format(city_data.get("pressure")) + " hpa\n<i>Humidity</i>: {}".format(city_data.get("humidity")) + "%" +
							"\n--------------------------------" +
							"\n<i>Sunrise</i>: {}".format(city_data.get("sunrise").strftime("%A %B %d, %Y %X %Z")) + "\n<i>Sunset</i>: {}".format(city_data.get("sunset").strftime("%A %B %d, %Y %X %Z")),
					"parse_mode": "html"
				}).json())
			else:
				print(self.sendMessage({
					"chat_id": chat_id, 
					"text": "There was an error with the city you entered. Please check the spelling and try again."
				}).json())

		elif command in ["/zipweather", "/zipweather@" + self.bot_info["username"]]:
			zip_data = {}
			self.prepareData(WeatherType.POSTAL_CODE, user_parameters, zip_data)

			#print(zip_data)

			if zip_data != {}:
				print(self.sendPhoto({
					"chat_id": chat_id,
					"photo": "http://openweathermap.org/img/wn/" + zip_data.get("icon") + "@4x.png", 
					"caption": "The current weather for " + zip_data.get("place") + ":" +
							"\n--------------------------------" +
							"\n" + zip_data.get("main") + "/" + zip_data.get("desc") + "\n<b>Temperature</b>: {}".format(zip_data.get("temp")) + " °F" +
							"\n<i>Feels like</i>: {}".format(zip_data.get("feel")) + " °F" +
							"\n<b>Low</b>: {}".format(zip_data.get("min_temp")) + " °F" + "\n<b>High</b>: {}".format(zip_data.get("max_temp")) + " °F" +
							"\n--------------------------------" +
							"\n<i>Pressure</i>: {}".format(zip_data.get("pressure")) + " hpa\n<i>Humidity</i>: {}".format(zip_data.get("humidity")) + "%" +
							"\n--------------------------------" +
							"\n<i>Sunrise</i>: {}".format(zip_data.get("sunrise").strftime("%A %B %d, %Y %X %Z")) + "\n<i>Sunset</i>: {}".format(zip_data.get("sunset").strftime("%A %B %d, %Y %X %Z")),
					"parse_mode": "html"
				}).json())
			else:
				print(self.sendMessage({
					"chat_id": chat_id, 
					"text": "There was an error with the postal code you entered. Please check the spelling and try again."
				}).json())
		#handling malformed/unsupported commands from
		#users this way results in weird behavior sometimes
		#(for example on a pin message event or upon inviting the bot to a chat)
		#it's best to just ignore interactions outside
		#the scope of valid commands for now
		#else:
		#	msg = {
		#		"chat_id": chat_id,
		#		"text": "I didn't quite get that, " + user_first_name + ". Please try a valid command."
		#	}
		#	print(self.sendMessage(msg).json())

	def kelvinToFahrenheit(self, temp):
		return (temp - 273.15) * 1.8000 + 32.00

	def kelvinToCelsius(self, temp):
		return temp - 273.15
		
	def onInit(self):
		print(self.setMyCommands(bot_commands).json())
		print(self.getMyCommands().json())

conf = {
	'/': {
		'tools.sessions.on': True,
		'tools.staticdir.root': os.path.abspath(os.getcwd())
	},
	'/static': {
		'tools.staticdir.on': True,
		'tools.staticdir.dir': './public'
	}
}

newBot = Bot(hook_data, conf)