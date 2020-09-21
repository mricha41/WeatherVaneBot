#weather bot example

#if you don't whish to set this
#just copy the file to the top-level
#folder and run it there w/out this
import sys
sys.path.append("../dokkaebi")
print(sys.path)

from enum import Enum

import string
import datetime
from timezonefinder import TimezoneFinder
from pytz import timezone

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
	]
}

#you'll need your own API key
#at api.openweathermap.org
openweather = {
	'key': config["OpenWeather"]["API_KEY"]
}

#bitly access
bitly = {
	"token": config["Bitly"]["TOKEN"]
}

class WeatherType(Enum):
	CITY = 0
	POSTAL_CODE = 1

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
		"""
		{
			'place': 'Kennesaw, GA - US:', 
			'latitude': 34.02, 'longitude': -84.62, 
			'local_timezone': <DstTzInfo 'America/New_York' LMT-1 day, 19:04:00 STD>, 
			'temp': 65.41, 'feel': 59.63, 'min_temp': 63, 'max_temp': 66.99, 
			'pressure': 1029, 'humidity': 52, 
			'main': 'Clear', 'desc': 'clear sky', 
			'icon': '01d', 'country': 'US', 
			'sunrise': datetime.datetime(2020, 9, 21, 7, 26, 12, tzinfo=<DstTzInfo 'America/New_York' EDT-1 day, 20:00:00 DST>), 
			'sunset': datetime.datetime(2020, 9, 21, 19, 36, 35, tzinfo=<DstTzInfo 'America/New_York' EDT-1 day, 20:00:00 DST>), 
			'name': 'Kennesaw'
		}
		"""
		fig = plotly.graph_objects.Figure(
		    data=[plotly.graph_objects.Bar(
		    	x=["Low", "Current", "High"],
		    	y=[params["min_temp"], params["temp"], params["max_temp"]]
		    )],
		    layout_title_text=params["place"] + "\n{}".format(params.get("timestamp")),
		)

		fig.update_layout(yaxis=dict(range=[-30, 130]))
		
		p = plotly.offline.plot(fig, include_plotlyjs=False, output_type='div')

		render = """
			<html>
          		<head><script src="https://cdn.plot.ly/plotly-latest.min.js"></script></head>
          			<body>""" + p + """
          			</body>
          	</html>"""

		return render

	def prepareData(self, type, user_parameters):
		self.payload = {}
		if type == WeatherType.CITY:
			self.weatherByCity(user_parameters)
		if type == WeatherType.POSTAL_CODE:
			self.weatherByPostalCode(user_parameters)

	def prepareResponse(self, res):
		if res != {}:
			tf = TimezoneFinder()

			if res.get("coord") and res["coord"] != None:
				self.payload.update({
					"latitude": res["coord"]["lat"],
					"longitude": res["coord"]["lon"],
					"local_timezone": timezone(tf.timezone_at(lng=res["coord"]["lon"], lat=res["coord"]["lat"]))
				})

			if res.get("main") and res["main"] != None:
				self.payload.update({
					"temp": res["main"]["temp"],
					"feel": res["main"]["feels_like"],
					"min_temp": res["main"]["temp_min"],
					"max_temp": res["main"]["temp_max"],
					"pressure": res["main"]["pressure"],
					"humidity": res["main"]["humidity"]
				})

			if res.get("weather") and res["weather"][0] != None:
				self.payload.update({
					"main": res["weather"][0]["main"],
					"desc": res["weather"][0]["description"],
					"icon": res["weather"][0]["icon"],
				})

			if res.get("sys") and res["sys"] != None:
				self.payload.update({
					"country": res["sys"]["country"],
					"sunrise": datetime.datetime.fromtimestamp(res["sys"]["sunrise"], tz=timezone(tf.timezone_at(lng=res["coord"]["lon"], lat=res["coord"]["lat"]))),
					"sunset": datetime.datetime.fromtimestamp(res["sys"]["sunset"], tz=timezone(tf.timezone_at(lng=res["coord"]["lon"], lat=res["coord"]["lat"]))),
					"timestamp": datetime.datetime.now(tz=timezone(tf.timezone_at(lng=res["coord"]["lon"], lat=res["coord"]["lat"]))).strftime("%A %B %d, %Y %I:%M:%S %p %Z")
				})

			if res.get("name") and res["name"] != None:
				self.payload.update({"name": res["name"]})

	def weatherByCity(self, user_parameters):
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
						#print('path 2')
					else:
						url = "https://api.openweathermap.org/data/2.5/weather?q=" + city.title() + "," + state + "&units=imperial&appid=" + openweather["key"]
						#print('path 3')
			else:
				url = "https://api.openweathermap.org/data/2.5/weather?q=" + city.title() + "&units=imperial&appid=" + openweather["key"]
				#print('path 4')

			print(url)

			res = requests.get(url).json()
			print(res)

			if res != None and res.get("cod") == 200:
				if state != None:
					self.payload.update({"place": res.get("name").title() + ", " + state.upper() + " - " + res.get("sys").get("country")})
				else:
					self.payload.update({"place": res.get("name").title() + " - " + res.get("sys").get("country")})

				self.prepareResponse(res)
			else:
				print("OpenWeatherMap query failed ({}): ".format(res.get("cod")) + res.get("message"))

	def weatherByPostalCode(self, user_parameters):
		postal_code = None
		country_code = None

		#comma-separated parameters processing
		#country could be given along with postal code
		if len(user_parameters) == 2: #postal code and country were given
			postal_code = " ".join(user_parameters[:(len(user_parameters) - 1)]).strip()
			print(postal_code)
			country_code = user_parameters[len(user_parameters) - 1].strip()
			print(country_code)
			
		else: #otherwise it was just a postal code
			postal_code = user_parameters
			print(postal_code)

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

			print(url)

			res = requests.get(url).json()
			print(res)

			if res != None and res.get("cod") == 200:
				self.payload.update({"place": res.get("name").title() + " - " + res.get("sys").get("country")})
				self.prepareResponse(res)
			else:
				print("OpenWeatherMap query failed ({}): ".format(res.get("cod")) + res.get("message"))

	def handleData(self, data):
		print(data)
		command = None
		if "message" in data:
			if "text" in data["message"]:
				#this will work both for single word commands
				#and commands with multiple text parameters
				command = data["message"]["text"].split(' ')[0] #grab command keyword...
				user_parameters = ""
				if data["message"]["text"].split(' ')[1:]:#split on spaces first...
					if "," in data["message"]["text"]:#split on commas if there...
						user_parameters = data["message"]["text"].split(',')
						#re-establish the city name if multi-word (for example ["san", "luis", "obispo", "ca", "us"] 
						#becomes reconstituted as ["san luis obispo", "ca", "us"] as you would want it to be)
						user_parameters[0] = " ".join(user_parameters[0].split(' ')[1:])
						print("user params: {}".format(user_parameters))
						print(user_parameters)
					else: #no commas so its just the city
						user_parameters = " ".join(data["message"]["text"].split(' ')[1:]) #again, could be a multi-word city...
						print("user params: {}".format(user_parameters))
						#print(user_parameters[0])
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
				self.prepareData(WeatherType.CITY, user_parameters)

				print(self.payload)

				import urllib.parse

				if self.payload != {}:
					d = str(urllib.parse.urlencode(self.payload))
					print(d)
					headers = {
					    'Authorization': bitly["token"],
					    'Content-Type': 'application/json',
					}

					data = { "long_url": hook_data["url"] + "/dash?" + d, "domain": "bit.ly" }

					shorten = requests.post('https://api-ssl.bitly.com/v4/shorten', headers=headers, json=data).json()
					short_url = shorten.get("link")
					print(self.sendMessage({
						"chat_id": chat_id, 
						"text": "Your dashboard has been created! Check it out - " + short_url
					}).json())
				else:
					print(self.sendMessage({
						"chat_id": chat_id, 
						"text": "There was an error with the city you entered. Please check the spelling and try again."
					}).json())

			elif command in ["/cityweather", "/cityweather@" + self.bot_info["username"]]:
				self.prepareData(WeatherType.CITY, user_parameters)

				#print(self.payload)

				if self.payload != {}:
					print(self.sendPhoto({
						"chat_id": chat_id,
						"photo": "http://openweathermap.org/img/wn/" + self.payload.get("icon") + "@4x.png", 
						"caption": "The current weather for " + self.payload.get("place") + ":" +
								"\n--------------------------------" +
								"\n" + self.payload.get("main") + "/" + self.payload.get("desc") + "\n<b>Temperature</b>: {}".format(self.payload.get("temp")) + " °F" +
								"\n<i>Feels like</i>: {}".format(self.payload.get("feel")) + " °F" +
								"\n<b>Low</b>: {}".format(self.payload.get("min_temp")) + " °F" + "\n<b>High</b>: {}".format(self.payload.get("max_temp")) + " °F" +
								"\n--------------------------------" +
								"\n<i>Pressure</i>: {}".format(self.payload.get("pressure")) + " hpa\n<i>Humidity</i>: {}".format(self.payload.get("humidity")) + "%" +
								"\n--------------------------------" +
								"\n<i>Sunrise</i>: {}".format(self.payload.get("sunrise").strftime("%A %B %d, %Y %X %Z")) + "\n<i>Sunset</i>: {}".format(self.payload.get("sunset").strftime("%A %B %d, %Y %X %Z")),
						"parse_mode": "html"
					}).json())
				else:
					print(self.sendMessage({
						"chat_id": chat_id, 
						"text": "There was an error with the city you entered. Please check the spelling and try again."
					}).json())
			elif command in ["/zipweather", "/zipweather@" + self.bot_info["username"]]:
				self.prepareData(WeatherType.POSTAL_CODE, user_parameters)

				#print(self.payload)

				if self.payload != {}:
					print(self.sendPhoto({
						"chat_id": chat_id,
						"photo": "http://openweathermap.org/img/wn/" + self.payload.get("icon") + "@4x.png", 
						"caption": "The current weather for " + self.payload.get("place") + ":" +
								"\n--------------------------------" +
								"\n" + self.payload.get("main") + "/" + self.payload.get("desc") + "\n<b>Temperature</b>: {}".format(self.payload.get("temp")) + " °F" +
								"\n<i>Feels like</i>: {}".format(self.payload.get("feel")) + " °F" +
								"\n<b>Low</b>: {}".format(self.payload.get("min_temp")) + " °F" + "\n<b>High</b>: {}".format(self.payload.get("max_temp")) + " °F" +
								"\n--------------------------------" +
								"\n<i>Pressure</i>: {}".format(self.payload.get("pressure")) + " hpa\n<i>Humidity</i>: {}".format(self.payload.get("humidity")) + "%" +
								"\n--------------------------------" +
								"\n<i>Sunrise</i>: {}".format(self.payload.get("sunrise").strftime("%A %B %d, %Y %X %Z")) + "\n<i>Sunset</i>: {}".format(self.payload.get("sunset").strftime("%A %B %d, %Y %X %Z")),
						"parse_mode": "html"
					}).json())
				else:
					print(self.sendMessage({
						"chat_id": chat_id, 
						"text": "There was an error with the postal code you entered. Please check the spelling and try again."
					}).json())
			else:
				msg = {
					"chat_id": chat_id,
					"text": "I didn't quite get that, " + user_first_name + ". Please try a valid command."
				}
				print(self.sendMessage(msg).json())

	def kelvinToFahrenheit(self, temp):
		return (temp - 273.15) * 1.8000 + 32.00

	def kelvinToCelsius(self, temp):
		return temp - 273.15
		
	def onInit(self):
		self.payload = {}
		print(self.setMyCommands(bot_commands).json())
		print(self.getMyCommands().json())

newBot = Bot(hook_data)