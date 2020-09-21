import json
import requests
import cherrypy

class Dokkaebi(object):
	"""
	Dokkaebi is a class for easily creating
	Telegram bots and interacting with users.
	
	Data Members:
	self.bot_info - json data with information about your bot from the Telegram API.
	self.webhook_config - user-supplied dictionary with hook information (see __init__).
	self.webhook_info - json data with information about your webhook from the Telegram API.
	self.update_received_count - number of updates received counted since the bot was instantiated.
	"""

	def __init__(self, hook):
		"""
		Dokkaebi bot construction requires passing in a dictionary of the following form, for example:
		hook = {
			'hostname': '127.0.0.1', #optional
			'port': 80, #optional
			'token': 'yourtelegrambottokenhere', #required 
			'url': 'https://yourwebhookurlhere.com', #optional
			'environment': "CherryPy Environment value" #optional
		}
		d = dokkaebi.Dokkaebi(hook)
		PRECONDITION:
		None
		POSTCONDITION:
		Dokkaebi class is constructed from the given dictionary values.
		"""
		self.webhook_config = hook
		self.update_received_count = 0

		if hook and hook != None and all (keys in hook for keys in ["hostname", "port", "url"]):
			print("Starting Dokkaebi bot...")
			print("Ctrl+C to quit")

			#make sure there is no live webhook before setting it
			self.deleteWebhook()

			#store current webhook info upon setting it successfully
			self.setWebhook()
			self.webhook_info = self.getWebhookInfo()

			#store the bot info
			self.bot_info = self.getMe()

			#hook for init work that
			#needs accomplished in derived classes
			#before the server starts
			self.onInit()

			print("running cherrypy version: " + cherrypy.__version__)

			#crank up a CherryPy server
			cherrypy.config.update({
			    #'environment': self.webhook_config["environment"],
			    'server.socket_host': self.webhook_config["hostname"],
			    'server.socket_port': self.webhook_config["port"],
			})
			cherrypy.quickstart(self, '/')
		else:
			print("Dokkaebi bot initializing without CherryPy...")

			#store the bot info
			self.bot_info = self.getMe()

			#hook for init work that
			#needs accomplished in derived classes
			#before the server starts
			self.onInit()

			print("Dokkaebi initialized successfully.")

	@cherrypy.expose
	@cherrypy.tools.json_in()
	def index(self):
		"""
		Handles all of the update logic for the Dokkaebi bot.
		Because this varies wildy depending on the application,
		simply calling a user-defined function was the easiest
		way of handling the issue. The caller must inherit from
		Dokkaebi and override the handleData(data) function to
		implement their own update logic:

		class Bot(dokkaebi.Dokkaebi):
			#overridden function...
			def handleData(data):
				print("do some stuff with the update data...")

		This enables the user to hook into the CherryPy server
		listening at the webhook base url and customize the
		update logic.

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		Requests are received on the assigned port at the webhook url provided.
		Additionally, processing of the updates is passed on to self.handleData(data)
		which is implemented in the user-defined override outside of this class.
		"""
		data = cherrypy.request.json

		#callback to a user-defined function
		#for handling updates
		self.handleData(data)

	def onInit(self):
		"""
		Override this method to hook into the constructor and
		handle tasks that need to be handled upon construction
		of the Dokkaebi class.
		"""

	def handleData(self, data):
		"""
		Override this method to hook into the update method and
		handle json data retrieved from Telegram webhook request
		"""

	def setWebhook(self, hook = None):
		"""
		Sets the Telegram Bot webhook, defaults to using the current hook information
		stored in Dokkaebi or by passing in a dictionary in the form:
		{"url": "https://yourwebhookurl.com"}

		RETURNS: boolean

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance may or may not have been constructed.

		POSTCONDITION:
		self.webhook_config["url"] is set, the request is made, and one of the following takes place:
			* request status code 200 received and True is returned indicating the request was successful and
			  the webhook is set on Telegram
			* request status code returned indicates one of the following types of errors:
				* internal server error
				* client error
				* request object returned
		See the Telegram Bot API documentation for more information about what
		status codes may be returned when a request is made to /setWebhook.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/setWebhook'
		if(hook == None):
			r = requests.post(url, data = {"url": self.webhook_config["url"]})
		else:
			self.webhook_config["url"] = hook["url"]
			r = requests.post(url, data = {"url": self.webhook_config["url"]})

		if(r.status_code == 200):
			print("Webhook set: " + self.webhook_config["url"])
		else:
			print("error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def getWebhookInfo(self):
		"""
		Retrieves and returns the current webhook info stored
		in the Dokkaebi bot.

		RETURNS: WebhookInfo json object
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance may or may not have been constructed.
		Dokkaebi bot may have had webhook data assigned on construction.
		
		POSTCONDITION:
		Dokkaebi sends the request to get the webhook information from Telegram. Upon success,
		a json object is printed to the console and the WebhookInfo json object is
		returned to the caller In the event of an error,
		the request object is returned after error is printed to the console. Also, see the
		Telegram Bot API documentation for what types of status codes to expect
		when making a request to /getWebhookInfo.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/getWebhookInfo'
		r = requests.get(url)
		if(r.status_code == 200):
			print("Webhook info:")
			print(r.json())
			return r.json()["result"]
		else:
			print("Webhook info could not be retrieved - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
				return r

	def deleteWebhook(self):
		"""
		Deletes the current webhook on Telegram and resets the internal webhook data
		stored in the Dokkaebi bot.

		RETURNS: boolean
		
		PRECONDITION:
		Dokkaebi bot must have webhook data assigned via the constructor. A Telegram
		webhook may or may not have been previously set. (see Telegram Bot API for /setWebhook,
		/getWebhookInfo, and /deleteWebhook)
		
		POSTCONDITION:
		Dokkaebi sends the request to get remove the webhook from Telegram and the internal
		Dokkaebi bot webhook data is reset to None. Upon success, the HTTP status code
		is printed to the console and the request returns True. Upon error, the status code is printed to the console
		along with the whole request object returned. (see Python requests documentation for more 
		information on what status codes could be returned from requests.post(...)). Also, see the
		Telegram Bot API documentation for what types of status codes to expect
		when making a request to /deleteWebhook.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/deleteWebhook'
		r = requests.post(url)
		if(r.status_code == 200):
			print("Webhook deleted...")
		else:
			print("Webhook could not be deleted - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def getMe(self):
		"""
		Retrieves the current information about your bot from the Telegram API.
		
		RETURNS: User json object

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.
		
		POSTCONDITION:
		If the request succeeds, a User json object with the bot info will be returned.
		Otherwise, the request failed with an error and the request object is printed
		to the console and returned. Also, see the Telegram Bot API documentation for 
		what types of status codes to expect when making a request to /getMe.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/getMe'
		r = requests.get(url)
		if(r.status_code == 200):
			print("Bot information:")
			print(r.json())
			return r.json()["result"]
		else:
			print("Bot information could not be retrieved - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
				return r

	def getUpdates(self, update_data = None):
		"""
		Gets updates from Telegram.
		{ 
			"offset": None, #optional - int identifier of the first update to be returned by Telegram. 
			"limit": , #optional - int limit set for the number of updates retrieved.
			"timeout": , #optional - int timeout in seconds used for polling.
			"allowed_updates": UpdateJsonObject #optional - array of Update json objects see https://core.telegram.org/bots/api#update.
		}

		RETURNS: Message json object

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, a Telegram Update json object is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		if(update_data != None):
			url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/getUpdates'
			r = requests.get(url, update_data)
		else:
			url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/getUpdates'
			r = requests.get(url)

		if(r.status_code == 200):
			print("Updates received...")
		else:
			print("Updates could not be retrieved - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
				
		return r

	def sendMessage(self, message_data):
		"""
		Sends a message to Telegram.
		The message_data parameter should be a dictionary of the following form:
		{ 
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs
			"text": "YOUR MESSAGE", #required - the message text you want to send.
			"parse_mode": None, #optional - string for html or markdown if desired (See Telegram API documentation).
			"disable_web_page_preview": None, #optional - boolean disables a web preview if sending a link.
			"disable_notification": None, #optional - boolean disables notification sound and sends message silently.
			"reply_to_message_id": None, #optional - optional id of the original message if the message is a reply.
			"reply_markup": {
				"keyboard": [
					["option 1"],
					["option 2"],
					["option 3"],
					["option 4"]
				]
			} #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}

		RETURNS: Message json object

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the message and the Message json object is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendMessage'
		if "reply_markup" in message_data:
			r = requests.post(url, json = message_data)
		else:
			r = requests.post(url, data = message_data)

		if(r.status_code == 200):
			print("Message sent...")
		else:
			print("Message could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
		
		return r

	def forwardMessage(self, message_data):
		"""
		Forward a message to Telegram.
		{
			"chat_id": CHATID, #required - string or integer according to Telegram API docs.
			"from_chat_id": FROMCHATID, #required - string or integer for the chat where the original message is from.
			"message_id": MESSAGEID, #required - integer id of the message being forwarded.
			"disable_notification": None, #optional - disable notification sound to send photo to user silently.
		}

		RETURNS: sent Message json object

		PRECONDITION:
		A Telegram bot has been created, the Dokkaebi instance has been constructed, and a
		message exists to forward.

		POSTCONDITION:
		On success, Telegram receives the forwarded message and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/forwardMessage'
		r = requests.post(url, data = message_data)

		if(r.status_code == 200):
			print("Message sent...")
		else:
			print("Message could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def sendPhoto(self, photo_data):
		"""
		Send a photo to Telegram.
		{
			"chat_id": CHATID, #required - string or integer according to Telegram API docs
			"photo": FILEORURL, #required - input file, file_id as string or url to photo as string (see Telegram API doc).
			"caption": "CAPTION", #optional - description of the photo.
			"parse_mode": None, #optional - html or markdown (see Telegram API doc).
			"disable_notification": None, #optional - disable notification sound to send photo to user silently.
			"reply_to_message_id": None, #optional - optional id of the original message if the message is a reply.
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}

		RETURNS: sent Message json object

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the photo request and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendPhoto'
		r = requests.post(url, data = photo_data)

		if(r.status_code == 200):
			print("Photo sent...")
		else:
			print("Photo could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def sendAudio(self, audio_data):
		"""
		Send audio to Telegram.
		{
			"chat_id": CHATID, #required - string or integer according to Telegram API docs
			"audio": FILEORURL, #required - input file, file_id as string or url to audio file as string (see Telegram API doc).
			"caption": "CAPTION", #optional - string description of the audio.
			"parse_mode": None, #optional - string html or markdown (see Telegram API doc).
			"duration": None, #optional - int duration in seconds.
			"performer": None, #optional - string performer name.
			"title": None, #optional - string title of audio.
			"thumb": {"thumb": open("path/to/thumb.jpg", "rb")}, #optional - input file or string (see Telegram API doc) 
			"disable_notification": None, #optional - disable notification sound to send audio to user silently.
			"reply_to_message_id": None, #optional - optional id of the original message if the message is a reply.
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}

		RETURNS: sent Message json object

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the audio request and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		if "thumb" in audio_data:
			url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendAudio?chat_id={}'.format(audio_data["chat_id"])
			r = requests.post(url, files = audio_data["thumb"], data = audio_data)
		else:
			url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendAudio'
			r = requests.post(url, data = audio_data)

		if(r.status_code == 200):
			print("Audio sent...")
		else:
			print("Audio could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def sendDocument(self, document_data):
		"""
		Send a document to Telegram.
		{
			"chat_id": CHATID, #required - string or integer according to Telegram API docs
			"document": FILEORURL, #required - input file, file_id as string or url to document as string (see Telegram API doc).
			"thumb": {"thumb": open("path/to/thumb.jpg", "rb")}, #optional - input file or string (see Telegram API doc)
			"caption": "CAPTION", #optional - string description of the document.
			"parse_mode": None, #optional - string html or markdown (see Telegram API doc).
			"disable_notification": None, #optional - disable notification sound to send document to user silently.
			"reply_to_message_id": None, #optional - optional id of the original message if the message is a reply.
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}

		RETURNS: sent Message json object

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the document request and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		if "thumb" in document_data:
			url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendDocument?chat_id={}'.format(document_data["chat_id"])
			r = requests.post(url, files = document_data["thumb"], data = document_data)
		else:
			url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendDocument'
			r = requests.post(url, data = document_data)

		if(r.status_code == 200):
			print("Document sent...")
		else:
			print("Document could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def sendVideo(self, video_data):
		"""
		Send a video to Telegram.
		{
			"chat_id": CHATID, #required - string or integer according to Telegram API docs
			"video": FILEORURL, #required - input file, file_id as string or url to video file as string (see Telegram API doc).
			"duration": None, #optional - int duration in seconds.
			"width": None, #optional - int width of video.
			"height": None, #optional - int height of video.
			"thumb": {"thumb": open("path/to/thumb.jpg", "rb")}, #optional - input file or string (see Telegram API doc)
			"caption": "CAPTION", #optional - string description of the video.
			"parse_mode": None, #optional - string html or markdown for video caption (see Telegram API doc).
			"supports_streaming": None, #optional - True if video can be streamed.			 
			"disable_notification": None, #optional - disable notification sound to send video to user silently.
			"reply_to_message_id": None, #optional - optional id of the original message if the message is a reply.
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}

		RETURNS: sent Message json object
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the video request and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		if "thumb" in video_data:
			url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendVideo?chat_id={}'.format(video_data["chat_id"])
			r = requests.post(url, files = video_data["thumb"], data = video_data)
		else:
			url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendVideo'
			r = requests.post(url, data = video_data)

		if(r.status_code == 200):
			print("Video sent...")
		else:
			print("Video could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r
	
	def sendAnimation(self, animation_data):
		"""
		Send an animation to Telegram.
		{
			"chat_id": CHATID, #required - string or integer according to Telegram API docs.
			"animation": "FILE", #required - InputFile or string according to Telegram API docs.
			"duration": None, #optional - int duration in seconds.
			"width": None, #optional - int width of animation.
			"height": None, #optional - int height of animation.
			"thumb": {"thumb": open("path/to/thumb.jpg", "rb")}, #optional - input file or string (see Telegram API doc).
			"caption": "CAPTION", #optional - string description of the animation.
			"parse_mode": None, #optional - string html or markdown for animation caption (see Telegram API doc).
			"disable_notification": None, #optional - disable notification sound to send animation to user silently.
			"reply_to_message_id": None, #optional - optional id of the original message if the message is a reply.
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}

		RETURNS: sent Message json object

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the animation request and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		if "thumb" in animation_data:
			url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendAnimation?chat_id={}'.format(animation_data["chat_id"])
			r = requests.post(url, files = animation_data["thumb"], data = animation_data)
		else:
			url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendAnimation'
			r = requests.post(url, data = animation_data)

		if(r.status_code == 200):
			print("Animation sent...")
		else:
			print("Animation could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
				
		return r

	def sendVoice(self, voice_data):
		"""
		Send a voice message to Telegram.
		{
			"chat_id": CHATID, #required - string or integer according to Telegram API docs.
			"voice": "FILE", #required - InputFile or string according to Telegram API docs.
			"caption": "CAPTION", #optional - string description of the voice.
			"parse_mode": None, #optional - string html or markdown for voice caption (see Telegram API doc).
			"duration": None, #optional - int duration in seconds.
			"disable_notification": None, #optional - disable notification sound to send voice to user silently.
			"reply_to_message_id": None, #optional - optional id of the original message if the message is a reply.
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}

		RETURNS: sent Message json object
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the voice request and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendVoice'
		r = requests.post(url, data = voice_data)

		if(r.status_code == 200):
			print("Voice sent...")
		else:
			print("Voice could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
				
		return r

	def sendVideoNote(self, video_note_data):
		"""
		Send a video note to Telegram.
		{
			"chat_id": CHATID, #required - string or integer according to Telegram API docs.
			"video_note": "FILE", #required - InputFile or string according to Telegram API docs.
			"duration": None, #optional - int duration in seconds.
			"length": None, #optional - int diameter of video note according to Telegram API docs.
			"thumb": {"thumb": open("path/to/thumb.jpg", "rb")}, #optional - input file or string (see Telegram API doc)
			"disable_notification": None, #optional - disable notification sound to send video note to user silently.
			"reply_to_message_id": None, #optional - optional id of the original message if the message is a reply.
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}

		RETURNS: sent Message json object
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the video note request and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		if "thumb" in video_note_data:
			url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendVideoNote?chat_id={}'.format(video_note_data["chat_id"])
			r = requests.post(url, files = video_note_data["thumb"], data = video_note_data)
		else:
			url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendVideoNote'
			r = requests.post(url, data = video_note_data)

		if(r.status_code == 200):
			print("Video note sent...")
		else:
			print("Video note could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
				
		return r

	def sendMediaGroup(self, media_group_data):
		"""
		Send a group of photos or videos as an album to Telegram.
		{
			"chat_id": CHATID, #required - string or integer according to Telegram API docs.
			"media": [
				{"type": "photo", "media": "URLTOPHOTO"},
				{"type": "photo", "media": "URLTOPHOTO"},
				...
			, # required - json-serialized array of InputMediaPhoto or InputMediaVideo (2-10 items).
			"disable_notification": None, #optional - disable notification sound to send media group to user silently.
			"reply_to_message_id": None #optional - optional id of the original message if the message is a reply.
		}

		RETURNS: array of sent Message json object
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the media group request and the array of Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendMediaGroup'
		r = requests.post(url, json = media_group_data)

		if(r.status_code == 200):
			print("Media group sent...")
		else:
			print("Media group could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
				
		return r

	def sendLocation(self, location_data):
		"""
		Send a location to Telegram.
		{
			"chat_id": CHATID, #required - string or integer according to Telegram API docs.
			"latitude": LAT, #required - float latitude of location.
			"longitude": LONG, #required - float longitude of location.
			"live_period": , #optional - period in seconds for which the location will be updated (60-86400 seconds).
			"disable_notification": None, #optional - disable notification sound to send location to user silently.
			"reply_to_message_id": None, #optional - optional id of the original message if the message is a reply.
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}
		
		RETURNS: sent Message json object
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the location request and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendLocation'
		r = requests.post(url, data = location_data)

		if(r.status_code == 200):
			print("Location sent...")
		else:
			print("Location could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def editMessageLiveLocation(self, location_data):
		"""
		Edit a live location message.
		{
			"chat_id": CHATID, #optional - string or integer according to Telegram API docs. (required if inline_message_id is not specified)
			"message_id": MESSAGEID, #optional - integer id of the live location message being edited. (required if inline_message_id is not specified)
			"inline_message_id": MESSAGEID, # optional - integer id of inline message (required if chat_id and message_id are not specified)
			"latitude": LAT, #required - float latitude of location.
			"longitude": LONG, #required - float longitude of location.
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}

		RETURNS: if bot owned the message a sent Message json object is returned, otherwise True is returned
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the edit live location request and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/editMessageLiveLocation'
		r = requests.post(url, data = location_data)

		if(r.status_code == 200):
			print("Location edit sent...")
		else:
			print("Location edit could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def stopMessageLiveLocation(self, location_data):
		"""
		Stop a live location message.
		{
			"chat_id": CHATID, #optional - string or integer according to Telegram API docs. (required if inline_message_id is not specified)
			"message_id": MESSAGEID, #optional - integer id of the live location message being edited. (required if inline_message_id is not specified)
			"inline_message_id": MESSAGEID, # optional - integer id of inline message (required if chat_id and message_id are not specified)
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}

		RETURNS: if bot owned the message a sent Message json object is returned, otherwise True is returned
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the stop live location request and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/stopMessageLiveLocation'
		r = requests.post(url, data = location_data)

		if(r.status_code == 200):
			print("Live location stopped...")
		else:
			print("Live location stop could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def sendVenue(self, venue_data):
		"""
		Send a venue to Telegram.
		{
			"chat_id": CHATID, #required - string or integer according to Telegram API docs.
			"latitude": LAT, #required - float latitude of venue.
			"longitude": LONG, #required - float longitude of venue.
			"title": "TITLE", #required - string title of the venue.
			"address": "ADDRESS", #required - string address of the venue.
			"foursquare_id": None, #optional - string foursquare id (see Telegram API doc).
			"foursquare_type": None, #optional - string foursquare type (see Telegram API doc).
			"disable_notification": None, #optional - disable notification sound to send venue to Telegram silently.
			"reply_to_message_id": None, #optional - optional id of the original message if the message is a reply.
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}
		
		RETURNS: sent Message json object
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the venue request and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendVenue'
		r = requests.post(url, data = venue_data)

		if(r.status_code == 200):
			print("Venue sent...")
		else:
			print("Venue could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r
	def sendContact(self, contact_data):
		"""
		Send a contact to Telegram.
		{
			"chat_id": CHATID, #required - string or integer according to Telegram API docs.
			"phone_number": "PHONENUMBER", #required - string contact's phone number.
			"first_name": "FIRSTNAME", #required - string contact's first name.
			"last_name": None, #optional - string contact's last name.
			"vcard": None, #optional - string contact's vcard.
			"disable_notification": None, #optional - disable notification sound to send contact to user silently.
			"reply_to_message_id": None, #optional - optional id of the original message if the message is a reply.
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}
		
		RETURNS: sent Message json object
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the contact request and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendContact'
		r = requests.post(url, data = contact_data)

		if(r.status_code == 200):
			print("Contact sent...")
		else:
			print("Contact could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def sendPoll(self, poll_data):
		"""
		Send a venue to Telegram.
		{
			"chat_id": CHATID, #required - string or integer according to Telegram API docs.
			"question": "YOUR QUESTION", #required - string poll question.
			"options": ["OPTION1", "OPTION2", ...], #required - array of string poll options.
			"is_anonymous": True, #optional - defaults to True, set to False if anonymity is not desirable.
			"type": "regular", #optional - defaults to "regular", set to "quiz" if desired.
			"allows_multiple_answers": False, #optional - defaults to False (ignored in "quiz" mode), set True if desired.
			"correct_option_id": None, #optional - integer 0-based index into options given, required for "quiz" mode, otherwise set if desired.
			"explanation": None, #optional - string explanation for correct answer if desired.
			"explanation_parse_mode": None, #optional - html or markdown if desired (see Telegram API doc).
			"open_period": None, #optional - integer time in seconds the poll is open (5-600 seconds, cannot be used with close_date).
			"close_date": None, #optional - integer date as a Unix timestamp when the poll should close (5-600 seconds after poll started, cannot be used with open_period).
			"is_closed": None, #optional - boolean pass in True to immediately end a poll, which could be useful in testing it.
			"disable_notification": None, #optional - disable notification sound to send venue to Telegram silently.
			"reply_to_message_id": None, #optional - optional id of the original message if the message is a reply.
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply.
		}
		
		RETURNS: sent Message json object
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		On success, Telegram receives the poll request and the Message json object
		is returned. 
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendPoll'
		r = requests.post(url, json = poll_data)

		if(r.status_code == 200):
			print("Poll sent...")
		else:
			print("Poll could not be sent - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

	def sendDice(self, dice_data):
		"""
		Send dice to the Telegram user.
		{ 
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"emoji": None, #optional - accepts a string with unicode value or copy/paste literal emoji (probably works).
			"disable_notification": None, #optional - boolean disables notification sound and sends dice silently.
			"reply_to_message_id": None, #optional - integer optional message id if the message is a reply.
			"reply_markup": None #optional - See Telegram API documentation, pass in InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply
		}

		RETURNS: sent Message json object

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The dice have been sent to the Telegram user and the request object is returned
		to the caller to process at their option.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendDice'
		r = requests.post(url, data = dice_data)

		if(r.status_code == 200):
			print("Dice sent...")
		else:
			print("Dice could not be set - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
		
		return r

	def sendChatAction(self, action_data):
		"""
		Send a chat action (indication that something is happening on the bot side) to Telegram.
		{ 
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"action": "ACTION"	#required - Type of action to broadcast. 
			#Choose one, depending on what the user is about to receive: 
			#typing for text messages, upload_photo for photos, record_video or upload_video for videos, 
			#record_audio or upload_audio for audio files, upload_document for general files, find_location for location data, 
			#record_video_note or upload_video_note for video notes.
		}

		RETURNS: True on success

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The chat action has been sent to the Telegram user and the request object is returned
		to the caller to process at their option.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/sendChatAction'
		r = requests.post(url, data = action_data)

		if(r.status_code == 200):
			print("Chat action sent...")
		else:
			print("Chat action could not be set - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
		
		return r

	def getUserProfilePhotos(self, profile_data):
		"""
		Get a list of profile photos from a Telegram user.
		{ 
			"user_id": USERCHATID, #required - integer according to Telegram API docs.
			"offset": None, #optional - integer sequential number of the first photo to be returned. All photos are returned by default.
			"limit": None #optional - integer number of photos to limit the results to (1-100 photos).
		}

		RETURNS: UserProfilePhotos json object

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The profile photo request has been sent to the Telegram and UserProfilePhotos json object is returned
		to the caller to process at their option.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/getUserProfilePhotos'
		r = requests.get(url, data = profile_data)

		if(r.status_code == 200):
			print("Profile photos received...")
		else:
			print("Profile photos could not be retrieved - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
		
		return r

	def getFile(self, file_data):
		"""
		Get information about a file and prepare it for downloading. This function may
		not behave like you expect it to, so it is strongly suggested to review the
		Telegram API documentation before using this.
		{
			"file_id": FILEID #required - int unique identifier for the file.
		}

		RETURNS: File json object
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The file request has been sent to the Telegram and a File json object is returned
		to the caller to process at their option.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/getFile'
		r = requests.get(url, data = file_data)

		if(r.status_code == 200):
			print("File received...")
		else:
			print("File could not be retrieved - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
		
		return r

	def kickChatMember(self, user_data):
		"""
		Remove a Telegram user from a chat (see Telegram API doc).
		{
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"user_id": USERID, #required - int unique id of user.
			"until_date": DATE #optional - int Unix timestamp.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The kick chat member request has been sent to the Telegram and True is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/kickChatMember'
		r = requests.post(url, data = user_data)

		if(r.status_code == 200):
			print("Member kicked from chat...")
		else:
			print("Member could not be kicked - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
		
		return r

	def unbanChatMember(self, user_data):
		"""
		Unban a previously kicked Telegram user from a chat (see Telegram API doc).
		{
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"user_id": USERID, #required - int unique id of user.
			"until_date": DATE #optional - int Unix timestamp.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The unban chat member request has been sent to the Telegram and True is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/unbanChatMember'
		r = requests.post(url, data = user_data)

		if(r.status_code == 200):
			print("Member unbanned from chat...")
		else:
			print("Member could not be unbanned - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def restrictChatMember(self, user_data):
		"""
		Restrict a Telegram user (see Telegram API doc).
		{
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"user_id": USERID, #required - int unique id of user.
			"permissions": {
				"can_send_messages": None, #optional - boolean send text messages, contacts, locations and venues
				"can_send_media_messages": None, #optional - boolean send audios, documents, photos, videos, video notes and voice notes
				"can_send_polls": None, #optional - boolean send polls
				"can_send_other_messages": None, #optional - boolean send animations, games, stickers and use inline bots
				"can_add_web_page_previews": None, #optional - boolean add web page previews to their messages
				"can_change_info" None, #optional - boolean change the chat title, photo and other settings
				"can_invite_users" None, #optional - boolean invite new users to the chat
				"can_pin_messages" None, #optional - boolean pin messages
			}, #required - ChatPermissions object (see Telegram API doc).
			"until_date": DATE #optional - int Unix timestamp.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The restrict chat member request has been sent to the Telegram and True is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/restrictChatMember'
		r = requests.post(url, json = user_data)

		if(r.status_code == 200):
			print("Member restrictions set...")
		else:
			print("Member could not be restricted - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def promoteChatMember(self, user_data):
		"""
		Promote a Telegram user in a chat (see Telegram API doc).
		{
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"user_id": USERID, #required - int unique id of user.
			"can_change_info": None, #optional - boolean true if admin can change chat info (title, photo, description, etc.).
			"can_post_messages": None, #optional - boolean true if admin can post messages to the chat.
			"can_edit_messages": None, #optional - boolean true if admin can edit messages in the chat.
			"can_delete_messages": None, #optional - boolean true if admin can delete messages in the chat.
			"can_invite_users": None, #optional - boolean true if admin can invite users to the chat.
			"can_restrict_members": None, #optional - boolean true if admin can restrict members in the chat.
			"can_pin_messages": None, #optional - boolean true if admin can pin messages in the chat.
			"can_promote_members": None #optional - boolean true if admin can promote members in a chat.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The promote chat member request has been sent to the Telegram and True is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/promoteChatMember'
		r = requests.post(url, data = user_data)

		if(r.status_code == 200):
			print("Member promoted...")
		else:
			print("Member could not be promoted - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def setChatAdministratorCustomTitle(self, user_data):
		"""
		Set a custom title for an administrator in a chat promoted by the bot (see Telegram API doc).
		{
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"user_id": USERID, #required - int unique id of user.
			"custom_title": "TITLE" #required - string custom title for the chat admin.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The set chat administrator title request has been sent to the Telegram and True is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/setChatAdministratorCustomTitle'
		r = requests.post(url, data = user_data)

		if(r.status_code == 200):
			print("Chat administrator custom title set...")
		else:
			print("Chat administrator custom title could not be set - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def setChatPermissions(self, permissions_data):
		"""
		Set default chat permissions for a chat (see Telegram API doc).
		{
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"permissions": {
				"can_send_messages": None, #optional - boolean send text messages, contacts, locations and venues
				"can_send_media_messages": None, #optional - boolean send audios, documents, photos, videos, video notes and voice notes
				"can_send_polls": None, #optional - boolean send polls
				"can_send_other_messages": None, #optional - boolean send animations, games, stickers and use inline bots
				"can_add_web_page_previews": None, #optional - boolean add web page previews to their messages
				"can_change_info" None, #optional - boolean change the chat title, photo and other settings
				"can_invite_users" None, #optional - boolean invite new users to the chat
				"can_pin_messages" None, #optional - boolean pin messages
			}, #required - ChatPermissions object (see Telegram API doc).
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The set chat permissions request has been sent to the Telegram and True is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/setChatPermissions'
		r = requests.post(url, json = permissions_data)

		if(r.status_code == 200):
			print("Chat permissions set...")
		else:
			print("Chat permissions could not be set - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def exportChatInviteLink(self, chat_data):
		"""
		Generate a new invite link for a chat (see Telegram API doc).
		{
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
		}

		RETURNS: string
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The export chat invite link request has been sent to the Telegram and the string is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/exportChatInviteLink'
		r = requests.get(url, data = chat_data)

		if(r.status_code == 200):
			print("Chat invite link exported...")
		else:
			print("Chat invite link could not be exported - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def setChatPhoto(self, photo_data, photo_file):
		"""
		Set the profile photo for the chat - does not work for private chats (see Telegram API doc).
		{
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"photo": YOURPHOTO #required - InputFile object according to Telegram API docs.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The set chat photo request has been sent to the Telegram and True is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/setChatPhoto?chat_id={}'.format(photo_data["chat_id"])
		r = requests.post(url, files = photo_file)
		
		if(r.status_code == 200):
			print("Chat photo set...")
		else:
			print("Chat photo could not be set - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def deleteChatPhoto(self, chat_data):
		"""
		Delete the profile photo for the chat - does not work for private chats (see Telegram API doc).
		{
			"chat_id": YOURCHATID #required - string or integer according to Telegram API docs.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The delete chat photo request has been sent to the Telegram and True is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/deleteChatPhoto'
		r = requests.post(url, data = chat_data)
		
		if(r.status_code == 200):
			print("Chat photo deleted...")
		else:
			print("Chat photo could not be deleted - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def setChatTitle(self, chat_data):
		"""
		Set the title of the chat - does not work for private chats (see Telegram API doc).
		{
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"title": "TITLE" #required - string title you want to set for the chat.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The set chat title request has been sent to the Telegram and True is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/setChatTitle'
		r = requests.post(url, data = chat_data)
		
		if(r.status_code == 200):
			print("Chat title set...")
		else:
			print("Chat title could not be set - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def setChatDescription(self, chat_data):
		"""
		Set the description of the chat - bot must be an administrator (see Telegram API doc).
		{
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"description": "DESCRIPTION" #required - string description you want to set for the chat.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The set chat description request has been sent to the Telegram and True is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/setChatDescription'
		r = requests.post(url, data = chat_data)
		
		if(r.status_code == 200):
			print("Chat description set...")
		else:
			print("Chat description could not be set - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def pinChatMessage(self, chat_data):
		"""
		Pin a message in a chat - bot must be an administrator (see Telegram API doc).
		{
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"message_id": MESSAGEID, #required - integer id of the live location message being edited. (required if inline_message_id is not specified)
			"disable_notification": None #optional - boolean disables notification sound and sends dice silently.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The pin chat message request has been sent to the Telegram and True is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/pinChatMessage'
		r = requests.post(url, data = chat_data)
		
		if(r.status_code == 200):
			print("Chat message pinned...")
		else:
			print("Chat message could not be pinned - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def unpinChatMessage(self, chat_data):
		"""
		Unpin a message in a chat - bot must be an administrator (see Telegram API doc).
		{
			"chat_id": YOURCHATID #required - string or integer according to Telegram API docs.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The unpin chat message request has been sent to the Telegram and True is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/unpinChatMessage'
		r = requests.post(url, data = chat_data)
		
		if(r.status_code == 200):
			print("Chat message unpinned...")
		else:
			print("Chat message could not be unpinned - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def leaveChat(self, chat_data):
		"""
		Make bot leave a chat (see Telegram API doc).
		{
			"chat_id": YOURCHATID #required - string or integer according to Telegram API docs.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The leave chat message request has been sent to the Telegram and True is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/leaveChat'
		r = requests.post(url, data = chat_data)
		
		if(r.status_code == 200):
			print("Left the chat...")
		else:
			print("Could not leave the chat - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def getChat(self, chat_data):
		"""
		Get information about a chat - returns a Chat json object (see Telegram API doc).
		{
			"chat_id": YOURCHATID #required - string or integer according to Telegram API docs.
		}

		RETURNS: Chat json object
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The get chat request has been sent to the Telegram and a Chat json object is returned
		to the caller to process at their option.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/getChat'
		r = requests.get(url, data = chat_data)

		if(r.status_code == 200):
			print("Chat data received...")
		else:
			print("Chat data could not be retrieved - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
		
		return r

	def getChatAdministrators(self, chat_data):
		"""
		Get a list of administrators in a chat (see Telegram API doc).
		{
			"chat_id": YOURCHATID #required - string or integer according to Telegram API docs.
		}

		RETURNS: array of ChatAdministrator json object
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The get chat administrators message request has been sent to the Telegram and the json is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/getChatAdministrators'
		r = requests.get(url, data = chat_data)
		
		if(r.status_code == 200):
			print("Chat administrators retrieved...")
		else:
			print("Could not retrieve chat administrators - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def getChatMembersCount(self, chat_data):
		"""
		Get the number of members in a chat (see Telegram API doc).
		{
			"chat_id": YOURCHATID #required - string or integer according to Telegram API docs.
		}

		RETURNS: int
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The get chat members message request has been sent to the Telegram and the json is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/getChatMembersCount'
		r = requests.get(url, data = chat_data)
		
		if(r.status_code == 200):
			print("Chat member count retrieved...")
		else:
			print("Could not retrieve chat member count - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def getChatMember(self, chat_data):
		"""
		Get information about a chat member (see Telegram API doc).
		{
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"user_id": USERCHATID #required - integer according to Telegram API docs.
		}

		RETURNS: ChatMember json object
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The get chat members message request has been sent to the Telegram and the json is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/getChatMember'
		r = requests.get(url, data = chat_data)
		
		if(r.status_code == 200):
			print("Chat member retrieved...")
		else:
			print("Could not retrieve chat member - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def setChatStickerSet(self, sticker_data):
		"""
		Set a new group sticker set in a chat - bot must be an administrator (see Telegram API doc).
		{
			"chat_id": YOURCHATID, #required - string or integer according to Telegram API docs.
			"sticker_set_name": "NAME" #required - string according to Telegram API docs.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The set chat sticker set message request has been sent to the Telegram and the json is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/setChatStickerSet'
		r = requests.post(url, data = sticker_data)
		
		if(r.status_code == 200):
			print("Chat sticker set has been set...")
		else:
			print("Could not set chat sticker set - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def deleteChatStickerSet(self, chat_data):
		"""
		Remove group sticker set from a chat - bot must be an administrator (see Telegram API doc).
		{
			"chat_id": YOURCHATID #required - string or integer according to Telegram API docs.
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The set chat sticker set message request has been sent to Telegram and the json is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/deleteChatStickerSet'
		r = requests.post(url, data = chat_data)
		
		if(r.status_code == 200):
			print("Chat sticker set has been deleted...")
		else:
			print("Could not delete chat sticker set - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def answerCallbackQuery(self, callback_data):
		"""
		Send answers to callback queries sent from inline keyboards (see Telegram API doc).
		{
			"callback_query_id": "ID", #required - string unique id of the query to be answered.
			"text": "TEXT", #optional - string text of the notification.
			"show_alert": None, #optional - boolean show an alert instead of a notification at the top of the screen.
			"url": None, #optional - string url to be opened by the user's client.
			"cache_time": #optional - int max time the callback should be cached on the user's client (default is zero).
		}

		RETURNS: boolean
		
		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.

		POSTCONDITION:
		The answer callback query request has been sent to Telegram and the json is returned on
		success.
		Otherwise, if the request failed with an error the request object is printed
		to the console and returned.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/answerCallbackQuery'
		r = requests.post(url, data = callback_data)
		
		if(r.status_code == 200):
			print("Answer callback query completed...")
		else:
			print("Could not complete the answer callback query - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)

		return r

	def setMyCommands(self, commands):
		"""
		Sets the command list for your bot programatically
		rather than through the Bot Father. Accepts an array
		of dictionary with the following form (up to 100 commands):

		#sets the list to empty:
		self.setMyCommands({"commands": []})
		commands = {
			"commands": [
				{"command": "COMMAND TEXT HERE", "description": "DESCRIPTION HERE"},
				{"command": "COMMAND TEXT HERE", "description": "DESCRIPTION HERE"},
				...
			]
		}

		RETURNS: boolean

		#sets the list with valid commands:
		self.setMyCommands(commands)

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed. 
		Either no list or a previous list of commands may exist.
		
		POSTCONDITION:
		If the request succeeds, the bot command list will be overwritten on Telegram and
		a request object returned to the caller for optional processing.
		If the request fails, Telegram should revert to the existing list or the default
		list if a list was never supplied to the Bot Father. Otherwise, if the request 
		failed with an error the request object is printed to the console and returned to the caller.
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/setMyCommands'
		r = requests.post(url, json = commands)
		if(r.status_code == 200):
			print("Commands set...")
		else:
			print("Commands could not be set - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
		
		return r

	def getMyCommands(self):
		"""
		Gets the current command list for your bot programatically
		rather than through the Bot Father. Returns a json object
		from the Telegram API.

		RETURNS: array of BotCommand json object

		PRECONDITION:
		A Telegram bot has been created and the Dokkaebi instance has been constructed.
		
		POSTCONDITION:
		The current command list will be returned as JSON if the
		request succeeds. Otherwise, if the request failed with an error 
		the request object is printed to the console and returned to the caller. 
		"""
		url = 'https://api.telegram.org/bot' + self.webhook_config["token"] + '/getMyCommands'
		r = requests.get(url)
		if(r.status_code == 200):
			print("Get command request received...")
		else:
			print("Commands could not be retrieved - error: " + format(r.status_code))
			if r and r is not None:
				print("Request object returned: \n" + r.text)
				
		return r

	def closeServer(self):
		"""
		STUB
		"""
		print("Server closed...")
		
		return