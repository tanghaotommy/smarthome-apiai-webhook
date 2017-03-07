#!/usr/bin/env python
#coding:utf-8
import urllib
import json
import os
import requests
import re
import time
import copy
import sys
from pymongo import MongoClient
import math
reload(sys)
sys.setdefaultencoding( "utf-8" )

import random
from flask import Flask
from flask import request
from flask import make_response

import logging
import mysql.connector
#from mysql.connector import errorcode

MAXDISTANCE = 300
GOOGLEMAPS_API_KEY = "AIzaSyABcAARrYGpUs-9PCD1B7tdl3tMaxGHBZU"
mysql_config = config = {
  'user': 'root',
  'password': 'password',
  'host': 'newdatabase.cii5tvbuf3ji.us-west-1.rds.amazonaws.com',
  'database': 'RestaurantsRecommendation'
}
flavor_taste = {
	'辣的': '川菜',
	'甜的': '上海菜'
}

answers_query_restaurants = ['你喜欢哪种口味的菜？（比如川菜，粤菜，火锅，上海菜，粥等等）', '你喜欢哪种风格的菜？（比如川菜，粤菜，火锅，上海菜，粥等等）']
answers_query_restaurants_location = ['好的，请稍等！正在搜寻中！']
answers_query_restaurants_taste = ['好的，%s是个很棒的选择哦。那你能告诉我你的位置么？这\
样我好帮你寻找符合条件的餐馆。你可以直接打你所在的地址，也可以发送你当前位置。（可以在公众号设置内允许我访问你的当前位置，这样以后就不用你输入地址啦！）', '好的，%s是个很棒的选择哦。\n那我使用你当前的位置进行查找可以嘛？\
或者你直接打你所在的地址，也可以发送你当前位置。']
answers_query_restaurants_unknownLocation = ['请问是%s嘛？', '对不起，我不知道这个是哪里。你能再说一遍么？']
answers_query_restaurants_withoutTaste = ['好的，没问题，交给我来！\n那你能告诉我你的位置么？这\
样我好帮你寻找符合条件的餐馆。你可以直接打你所在的地址，也可以发送你当前位置。（可以在公众号设置内允许我访问你的当前位置，这样以后就不用你输入地址啦！）', '好的，没问题，交给我来！\n那我使用你当前的位置进行查找可以嘛？\
或者你直接打你所在的地址，也可以发送你当前位置。']
answers_query_taste = ['你是想让我给你推荐%s嘛？', '你是想吃%s嘛？']
answers_query_restaurants_closer = ['这家叫%s（%s）的稍微近一些。它的招牌菜是%s。\n您距离它有%skm。\n你喜欢嘛?', 
'对不起啊，我找不到更近的餐馆了。最近的就是这家叫%s（%s）的。它的招牌菜是%s。您距离它有%skm。\n你喜欢嘛？']
answers_query_restaurants_show = ['我觉得这家叫%s（%s）的感觉不错。它的招牌菜是%s。\n您距离它有%skm。\n你喜欢嘛?']
answers_query_restaurants_moreInformation = ["他们家的地址是%s。\n人均大概在$%s左右。"]
answers_query_restaurants_next = [answers_query_restaurants_show[0], "我没有更多的啦，只能从头再开始一遍咯！\n" + answers_query_restaurants_show[0]]

class Mysql(object):

	def connect(self, config):
		try:
		  self.cnx = mysql.connector.connect(**config)
		  return None
		except err:
			print err
			self.cnx = None
			return err
		else:
		  self.cnx.close()
		  self.cnx = None
		  return 0

	def close(self):
		if self.cnx: self.cnx.close(); self.cnx=None;

	def query(self, query,schema=None):
		cursor = self.cnx.cursor()

		cursor.execute(query)
		result = []
		for i, row in enumerate(cursor):
			if schema == None:
				result.append(row)
			else:
				dict = {}
				for j, column in enumerate(row):
					#print j
					#print column
					if j >= len(schema):
						break
					if isinstance(column, unicode):
						dict[schema[j]] = column.encode('utf-8')
					else:
						dict[schema[j]] = column
				result.append(dict)
		#print result
		# for (first_name, last_name, hire_date) in cursor:
		#   print("{}, {} was hired on {:%d %b %Y}".format(
		#     last_name, first_name, hire_date))

		cursor.close()
		return result
	def __del__(self):
		if self.cnx: self.cnx.close(); self.cnx=None;


# Flask app should start in global layout
app = Flask(__name__)
print ('嘿嘿')

@app.route('/user_location', methods=['POST'])
def user_location():
	req = request.get_json(silent=True, force=True)

	print("Request to user_location:")
	print(json.dumps(req, indent=4))

	res = "Success"

	client = MongoClient()
	db = client.wechat

	if db.UserLocation.find({"user_id": req['user_id']}).count() >= 1:
		#db.UserLocation.update({"user_id": req['user_id']}, {"user_id": req['user_id'], "timestamp": time.time(), "location": {"latitude": req['latitude'], "longitude": req['longitude']}})
		db.UserLocation.update({"user_id": req['user_id']}, {"$set": {"timestamp": time.time(), "location": {"latitude": req['latitude'], "longitude": req['longitude']}}})
		print "Update user location!"
	else:
		db.UserLocation.insert_one({"user_id": req['user_id'], "timestamp": time.time(), "location": {"latitude": req['latitude'], "longitude": req['longitude']}})
		print "Insert user location!"
	client.close()
	# user_location = db.UserLocation.find({"user_id": req['user_id']},{"_id": False})[0]
	# print user_location

	res = json.dumps(res, indent=4)
	print(res)
	r = make_response(res)
	r.headers['Content-Type'] = 'application/json'
	return r

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = makeWebhookResult(req)

    res = json.dumps(res, indent=4)
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

@app.route('/smarthome', methods=['POST'])
def smarthome():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = makeResponse(req)

    res = json.dumps(res, indent=4)
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

@app.route('/check_location', methods=['POST'])
def check_location():
   
    req = request.get_json(silent=True, force=True)
    print("RequestFromWeChat User Location:")
    print(json.dumps(req, indent=4))

    res = googleGeocode(req)

    res = json.dumps(res, indent=4)
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

@app.route('/restaurantsRec', methods=['POST'])
def restaurantsRec():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = makeResponse2(req)

    res = json.dumps(res, indent=4)
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

def distance(LatA, LngA, LatB, LngB):
	#http://www.movable-type.co.uk/scripts/latlong.html
	phi1 = math.radians(LatA)
	phi2 = math.radians(LatB)
	deltaPhi = math.radians(LatB - LatA)
	deltaLambda = math.radians(LngB - LngA)

	a = math.sin(deltaPhi/2)*math.sin(deltaPhi/2) + math.cos(phi1)*math.cos(phi2)*math.sin(deltaLambda/2)*math.sin(deltaLambda/2)
	c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
	# C = math.sin(LatA)*math.sin(LatB)*math.cos(LngA-LngB) + math.cos(LatA)*math.cos(LatB)
	R = 6371.004
	# distance = round(R*math.acos(C)*math.pi/180, 1)
	distance = R * c
	return round(distance, 1)

def googleGeocode(req):
	latitude = req['latitude']
	longitude = req['longitude']
	address = str(latitude) + " " + str(longitude)
	address = re.sub(" ", '+', address)
	print address
	url = "https://maps.googleapis.com/maps/api/geocode/json?address=%s&key=%s"
	url = url % (address, GOOGLEMAPS_API_KEY)
	r = requests.get(url)
	response = r.json()
	print response
	res = {}
	if response['status'] == 'OK':
		formatted_address = response['results'][0]['formatted_address']
		speech = answers_query_restaurants_unknownLocation[0] % (formatted_address)
		res["contextOut"] = [{"name": "user_asks4_restaurants_withunknownlocation","parameters": {"location.original": address, "location": {'formatted_address': formatted_address,'location': response['results'][0]['geometry']['location']},},"lifespan": 3}]
	else:
		speech = answers_query_restaurants_unknownLocation[1]
	res["speech"] = speech
	res["displayText"] = speech
	res["source"] = "shokse-restaurants-recommendation"
	return res

def clearContexts(contexts):
	for context in contexts:
		context["lifespan"] = 0
	return contexts

def deleteContext(contexts, name):
	for context in contexts:
		if context["name"] == name:
			context["lifespan"] = 0
			break
	return contexts

def extendContext(contexts, name, lifespan):
	for context in contexts:
		if context["name"] == name:
			context["lifespan"] = lifespan
			break
	return contexts

def findContext(contexts, name):
	for context in contexts:
		if context["name"] == name:
			return context
	return None

def getRestaurants(contexts, LatA, LngA, location_original = "", formatted_address = ""):
	contextOut = []
	taste = findContext(contexts, "user_asks4_restaurants_withtaste")["parameters"]["taste"]
	if taste == '': taste = '-1'
	dish = findContext(contexts, "user_asks4_restaurants_withtaste")["parameters"]["dish"]
	if dish == '': dish = '-1'
	flavor = findContext(contexts, "user_asks4_restaurants_withtaste")["parameters"]["flavor"].encode('utf-8')
	print flavor
	print flavor_taste
	if flavor_taste.has_key(flavor):
		taste = flavor_taste[flavor]
	mysql = Mysql()
	if(mysql.connect(mysql_config) == None):
		schema = ['id', 'name_en', 'name_cn', 'rating', 'type', 'signature', 'price_average', 'address', 'phone', 
'hour', 'city', 'state', 'zip', 'website', 'latitude', 'longitude']
		if taste == "all":
			results = mysql.query("SELECT * FROM Restaurants", schema)
		else:
			results = mysql.query("SELECT * FROM Restaurants WHERE type LIKE '%%%s%%' OR signature LIKE '%%%s%%'" % (taste, dish), schema)
		mysql.close()
		# print 'LatA' + str(LatA)
		# print 'LngA' + str(LngA)
		if len(results) > 0:
			distance_map = {}
			for row in results:
				LatB = row['latitude']
				LngB = row['longitude']
				dist = distance(LatA, LngA, LatB, LngB)
				if dist <= MAXDISTANCE:
					distance_map[row['id']] = dist

			sorted_key_list = sorted(distance_map, key=distance_map.get)

			if len(sorted_key_list) >= 1:
				mysql.connect(mysql_config)
				item = mysql.query("SELECT * FROM Restaurants WHERE id=%d" % (sorted_key_list[0]), schema)[0]
				mysql.close()

				context = [{"name": "restaurants_recommended", "parameters": {
				"lists": sorted_key_list,
				"max": len(sorted_key_list), 
				"current": 0,
				"user_location": {
					"location.original": location_original,
					"location": {
						"formatted_address": formatted_address,
						"location": {"lat": LatA, "lng": LngA}}}},
				"lifespan": 3}]
				contextOut = clearContexts(contexts)
				contextOut.extend(context)
				# print sorted_key_list[0]
				# print 'LatB' + str(results[sorted_key_list[0]]['latitude'])
				# print 'LngB' + str(results[sorted_key_list[0]]['longitude'])
				# print str(distance(LatA, LngA, results[sorted_key_list[0]-1]['latitude'], results[sorted_key_list[0]]['longitude']))
				speech = answers_query_restaurants_show[0] % (item['name_cn'], item['name_en'], item['signature'], str(distance_map[sorted_key_list[0]]))
			else:
				contextOut = clearContexts(result.get("contexts"))
				speech = "哎呀，对不起，在你附近我找不到符合条件的餐馆。"
		else:
			contextOut = clearContexts(result.get("contexts"))
			speech = "哎呀，对不起，在你附近我找不到符合条件的餐馆。"
	else:
		speech = '哎呀！数据库出了点小问题！等我下！'
	return speech, contextOut

def makeResponse2(req):
	action = req.get("result").get("action")
	result = req.get("result")
	user_id = req.get("sessionId")
	parameters = result.get("parameters")
	res = {}
	print action
	speech = '出错啦！！！'

	if action == 'query.restaurants.closer':
		context = findContext(result["contexts"], "restaurants_recommended")
		lists = context["parameters"]["lists"]
		current = context["parameters"]["current"]
		schema = ['id', 'name_en', 'name_cn', 'rating', 'type', 'signature', 'price_average', 'address', 'phone', 
'hour', 'city', 'state', 'zip', 'website', 'latitude', 'longitude']
		
		user_location = context["parameters"]["user_location"]
		if current > 0:
			current -= 1
			mysql = Mysql()
			mysql.connect(mysql_config)
			item = mysql.query("SELECT * FROM Restaurants WHERE id=%d" % (lists[current]), schema)[0]
			mysql.close()

			LatA = item["latitude"]
			LngA = item["longitude"]
			LatB = float(user_location["location"]["location"]["lat"])
			LngB = float(user_location["location"]["location"]["lng"])

			_distance = distance(LatA, LngA, LatB, LngB)
			speech = answers_query_restaurants_closer[0] % (item['name_cn'], item['name_en'], item['signature'], str(_distance))
			
			context["parameters"]["current"] = current
			contextOut = [{"name": "restaurants_recommended", "parameters": context["parameters"], "lifespan": 3}]
			res["contextOut"] = clearContexts(result.get("contexts"))
			res["contextOut"].extend(contextOut)
		else:
			current = 0
			context["parameters"]["current"] = current
			contextOut = [{"name": "restaurants_recommended", "parameters": context["parameters"], "lifespan": 3}]
			res["contextOut"] = clearContexts(result.get("contexts"))
			res["contextOut"].extend(contextOut)

			mysql = Mysql()
			mysql.connect(mysql_config)
			item = mysql.query("SELECT * FROM Restaurants WHERE id=%d" % (lists[current]), schema)[0]
			mysql.close()

			LatA = item["latitude"]
			LngA = item["longitude"]
			LatB = float(user_location["location"]["location"]["lat"])
			LngB = float(user_location["location"]["location"]["lng"])

			_distance = distance(LatA, LngA, LatB, LngB)
			speech = answers_query_restaurants_closer[1] % (item['name_cn'], item['name_en'], item['signature'], str(_distance))


	if action == 'query.taste':
		taste = parameters["taste"].encode('utf-8')
		dish = parameters["dish"].encode('utf-8')
		flavor = parameters["flavor"].encode('utf-8')
		speech = answers_query_taste[random.randint(0, len(answers_query_taste) - 1)] % (taste + dish + flavor)
		res['contextOut'] = clearContexts(result.get("contexts"))
		res['contextOut'] = extendContext(res['contextOut'], "user_mentions_taste", 3)


	if action == 'query.taste.positive':
		taste = findContext(result["contexts"], "user_mentions_taste")["parameters"]["taste"].encode('utf-8')
		dish = findContext(result["contexts"], "user_mentions_taste")["parameters"]["dish"].encode('utf-8')
		flavor = findContext(result["contexts"], "user_mentions_taste")["parameters"]["flavor"].encode('utf-8')
		client = MongoClient()
		contextOut = {"name": "user_asks4_restaurants_withTaste", 
		"parameters": {
			"taste": taste,
			"dish": dish,
			"flavor": flavor},
		"lifespan": 5}
		res["contextOut"] = clearContexts(result.get("contexts"))
		res["contextOut"].append(contextOut)
		db = client.wechat
		if db.UserLocation.find({"user_id": user_id}).count() >= 1:
			speech = answers_query_restaurants_taste[1] % (taste + dish + flavor)
		else:
			speech = answers_query_restaurants_taste[0] % (taste + dish + flavor)
		client.close()

	if action == 'query.restaurant':
		restaurant = parameters['restaurant_chinese']
		if not restaurant == "":
			mysql = Mysql()
			mysql.connect(mysql_config)
			print restaurant
			schema = ['id', 'name_en', 'name_cn', 'rating', 'type', 'signature', 'price_average', 'address', 'phone', 
'hour', 'city', 'state', 'zip', 'website', 'latitude', 'longitude']
			results = mysql.query("SELECT * FROM Restaurants WHERE name_en = '%s'" % (restaurant), schema)
			if len(results) >= 1:
				speech = "你说的一定是" + results[0]['name_cn'] + "。它在" + results[0]['address'] + "。他们家的招牌菜是" + results[0]['signature'] + "。我说的对不对呀！"
			else:
				speech = "哎呀，我不知道这是哪家店哎！过几天再来问问看呢。"
		else:
			speech = "你在说什么呀？"
			
	if action == 'query.restaurants':
		if result.has_key("contexts"): res["contextOut"] = clearContexts(result.get("contexts"))
		if not ((parameters["taste"] == "" and parameters["dish"] == "" and parameters["flavor"] == "")):
			client = MongoClient()
			db = client.wechat
			if db.UserLocation.find({"user_id": user_id}).count() >= 1:
				speech = answers_query_restaurants_taste[1] % (parameters.get('taste') + parameters.get('flavor') + parameters.get('dish'))
			else:
				speech = answers_query_restaurants_taste[0] % (parameters.get('taste') + parameters.get('flavor') + parameters.get('dish'))
			client.close()
			contextOut = [{"name": "user_asks4_restaurants_withtaste", "parameters": {
          "taste.original": "",
          "taste": parameters["taste"],
          "dish": parameters["dish"],
          "dish.original": "",
          "flavor": parameters["flavor"],
          "flavor.original": ""
        },
        "lifespan": 5}]
			if not (res["contextOut"] == ""):
				res["contextOut"].extend(contextOut)
			else:
				res["contextOut"] = {"contextOut": contextOut}
		else: 
			speech = answers_query_restaurants[random.randint(0, len(answers_query_restaurants) - 1)]
			contextOut = [{"name": "user_asks4_restaurantsrec", "parameters": {
			"taste.original": "",
			"taste": "",
			"dish": "",
			"dish.original": "",
			"flavor": "",
			"flavor.original": ""
			},
			"lifespan": 3}]
			if not (res["contextOut"] == ""):
				res["contextOut"].extend(contextOut)
			else:
				res["contextOut"] = {"contextOut": contextOut}
		print '123'

	if action == 'delete.unknownLocation':
		speech = "好吧，那是哪里呀？"
		res["contextOut"] = deleteContext(result["contexts"], "user_asks4_restaurants_withunknownlocation")
		context = findContext(result["contexts"], "user_asks4_restaurants_withtaste")
		if context and context['lifespan'] <= 1:
			speech = "哎呀，地址搞错好多次啦～我有点笨记不住那么多，所以被搞糊涂了。\n给我次机会，我们重头再来一次吧！如果地址老是不对你就给我发位置啦！"
			res["contextOut"] = clearContexts(result.get("contexts"))

	if action == 'query.restaurants.location':
		client = MongoClient()
		db = client.wechat
		document = db.UserLocation.find({"user_id": user_id})[0]
		print document
		location = document['location']
		print location
		LatA = float(location['latitude'])
		LngA = float(location['longitude'])
		print LatA
		print LngA
		client.close()
		speech, res['contextOut'] = getRestaurants(LatA=LatA, LngA=LngA, contexts=result.get("contexts"))

	if action == 'query.restaurants.taste':
		client = MongoClient()
		db = client.wechat
		if db.UserLocation.find({"user_id": user_id}).count() >= 1:
			speech = answers_query_restaurants_taste[1] % (parameters.get('taste') + parameters.get('dish') + parameters.get('flavor'))
		else:
			speech = answers_query_restaurants_taste[0] % (parameters.get('taste') + parameters.get('dish') + parameters.get('flavor'))
		client.close()

	if action == 'query.restaurants.unknownLocation':
		address = result.get('resolvedQuery')
		address = re.sub(" ", '+', address)
		url = "https://maps.googleapis.com/maps/api/geocode/json?address=%s&key=%s"
		url = url % (address, GOOGLEMAPS_API_KEY)
		r = requests.get(url)
		response = r.json()
		if response['status'] == 'OK':
			formatted_address = response['results'][0]['formatted_address']
			speech = answers_query_restaurants_unknownLocation[0] % (formatted_address)
			res["contextOut"] = [{"name": "user_asks4_restaurants_withunknownlocation","parameters": {"location.original": result.get('resolvedQuery'), "location": {'formatted_address': formatted_address,'location': response['results'][0]['geometry']['location']},},"lifespan": 3}]
		else:
			speech = answers_query_restaurants_unknownLocation[1]

	if action == 'query.restaurants.show':
		for context in result.get('contexts'):
			if context['name'] == 'user_asks4_restaurants_withunknownlocation':
				LatA = context['parameters']['location']['location']['lat']
				LngA = context['parameters']['location']['location']['lng']
				break
		speech, res['contextOut'] = getRestaurants(LatA=LatA, LngA=LngA, contexts=result.get("contexts"), 
			formatted_address=context['parameters']['location']['formatted_address'], 
			location_original=context['parameters']['location.original'])

	if action == 'query.restaurants.next':
		context = findContext(result["contexts"], "restaurants_recommended")
		lists = context["parameters"]["lists"]
		current = context["parameters"]["current"] + 1
		schema = ['id', 'name_en', 'name_cn', 'rating', 'type', 'signature', 'price_average', 'address', 'phone', 
'hour', 'city', 'state', 'zip', 'website', 'latitude', 'longitude']
		
		user_location = context["parameters"]["user_location"]
		if current < context["parameters"]["max"] - 1:
			mysql = Mysql()
			mysql.connect(mysql_config)
			item = mysql.query("SELECT * FROM Restaurants WHERE id=%d" % (lists[current]), schema)[0]
			mysql.close()

			LatA = item["latitude"]
			LngA = item["longitude"]
			LatB = float(user_location["location"]["location"]["lat"])
			LngB = float(user_location["location"]["location"]["lng"])

			_distance = distance(LatA, LngA, LatB, LngB)
			speech = answers_query_restaurants_next[0] % (item['name_cn'], item['name_en'], item['signature'], str(_distance))
			context["parameters"]["current"] = current
			contextOut = [{"name": "restaurants_recommended", "parameters": context["parameters"], "lifespan": 3}]
			res["contextOut"] = clearContexts(result.get("contexts"))
			res["contextOut"].extend(contextOut)
		else:
			current = 0
			context["parameters"]["current"] = current
			contextOut = [{"name": "restaurants_recommended", "parameters": context["parameters"], "lifespan": 3}]
			res["contextOut"] = clearContexts(result.get("contexts"))
			res["contextOut"].extend(contextOut)

			mysql = Mysql()
			mysql.connect(mysql_config)
			item = mysql.query("SELECT * FROM Restaurants WHERE id=%d" % (lists[current]), schema)[0]
			mysql.close()

			LatA = item["latitude"]
			LngA = item["longitude"]
			LatB = float(user_location["location"]["location"]["lat"])
			LngB = float(user_location["location"]["location"]["lng"])

			_distance = distance(LatA, LngA, LatB, LngB)
			speech = answers_query_restaurants_next[1] % (item['name_cn'], item['name_en'], item['signature'], str(_distance))	

	if action == 'query.restaurants.moreInformation':
		context = findContext(result["contexts"], "restaurants_recommended")
		lists = context["parameters"]["lists"]
		current = context["parameters"]["current"]
		mysql = Mysql()
		mysql.connect(mysql_config)
		schema = ['id', 'name_en', 'name_cn', 'rating', 'type', 'signature', 'price_average', 'address', 'phone', 
'hour', 'city', 'state', 'zip', 'website', 'latitude', 'longitude']
		item = mysql.query("SELECT * FROM Restaurants WHERE id=%d" % (lists[current]), schema)[0]
		mysql.close()

		res["contextOut"] = clearContexts(result.get("contexts"))
		contextOut = [{"name": "restaurants_recommended_accepted", "parameters": {
		"current": current},
		"lifespan": 3}]
		res["contextOut"].extend(contextOut)

		speech = answers_query_restaurants_moreInformation[0] % (item["address"], item["price_average"])
		#speech = result.get('resolvedQuery')

	if action == 'query.restaurants.withoutTaste':
		client = MongoClient()
		db = client.wechat
		if db.UserLocation.find({"user_id": user_id}).count() >= 1:
			speech = answers_query_restaurants_withoutTaste[1]
		else:
			speech = answers_query_restaurants_withoutTaste[0] 
		client.close()
		res["contextOut"] = [{"name": "user_asks4_restaurants_withtaste", "parameters": {
		"taste.original": "",
		"taste": "all",
		"dish": "",
		"dish.original": "",
		"flavor": "",
		"flavor.original": ""},
		"lifespan": 5}]

	if action == 'test':
		wechat = {
			"wechat": [{
    				"title": '我觉得这家不错，你喜欢嘛？',
    				"description": '<a href="http://54.183.198.179/UploadedFaceImages/1483855032.jpg">店面信息</a>',
    				"picurl": 'http://54.183.198.179/UploadedFaceImages/1483855032.jpg',
    				"url": 'http://nodeapi.cloudfoundry.com/'
  			}]
		}
		speech = '<a href="http://54.183.198.179/UploadedFaceImages/1483855032.jpg">店面信息</a>'
		#res["data"] = wechat
                speech = "<a href='http://maps.google.com/maps?&z=10&q=34.0800231+-118.1026794'>a place</a>"

	print("Response:" + str(speech))
	res["speech"] = speech
	res["displayText"] = speech
	res["source"] = "shokse-restaurants-recommendation"

	return res;


def makeResponse(req):
	action = req.get("result").get("action")
	result = req.get("result")
	facebook_userId = str(req.get("sessionId"))
	parameters = result.get("parameters")
	res = {}

	if action == "action.uploadphoto":
		print("Add face picture to training set!")
		content = {
			"Type": "AddFace",
			"Id": facebook_userId
		}
		print content
		r = requests.post("http://localhost/order.php", data=json.dumps(content))
		response = r.json()
		print response
		if response.get("Status") == 0:
			speech = "I have added this photo to the database. Our facial recognition is more precise ever before!"
		else:
			speech = "Sorry, I meet some errors. Please try again later!"

	if action == "action.register":
		print("New user registers!")
		content = {
			"Type": "register",
			"Id": facebook_userId
		}
		print content
		r = requests.post("http://localhost/register.php", data=json.dumps(content))
		response = r.json()
		print response
		if response.get("Status") == 0:
			speech = "You have successfully registered! Welcome, I am now your home assistant! What Can I do for you?"
		else:
			speech = "Sorry, I meet some errors. Please try again later!"
			
	if action == "action.openfrontdoor":
		print("Open Front Door!")
		content = {
		"Type": "OpenDoor",
		"Id": facebook_userId
		}
		r = requests.post("http://localhost/order.php", data=json.dumps(content))
		response = r.json()
		if response.get("Status") == 0:
			speech = "Your front door is opened!"
		elif response.get("Status") == 2:
			speech = "Oh, it seems your are not registered yet. Do you want to register right now?"
			res["contextOut"] = [{"name":"register", "lifespan":2}]
		else:
			speech = "Sorry, I meet some errors. Please try again later!"

	if action == "action.sendalert":
		print("Send Alert!")
		content = {
		"Type": "SendAlert",
		"Id": facebook_userId
		}
		r = requests.post("http://localhost/order.php", data=json.dumps(content))
		response = r.json()
		if response.get("Status") == 0:
			speech = "I have set the beep running!"
		elif response.get("Status") == 2:
			speech = "Oh, it seems your are not registered yet. Do you want to register right now?"
			res["contextOut"] = [{"name":"register", "lifespan":2}]
		else:
			speech = "Sorry, I meet some errors. Please try again later!"

	if action == "action.viewphoto":
		print("ViewPhoto!")
		content = {
			"Type": "ViewPhoto",
			"Id": facebook_userId
		}
		r = requests.post("http://54.183.198.179/order.php", data=json.dumps(content))
		print r.json()
		response = r.json()
		if response.get("Status") == 0:
			speech = "Sure! Wait a moment, picture is on its way!"
		elif response.get("Status") == 2:
			speech = "Oh, it seems your are not registered yet. Do you want to register right now?"
			res["contextOut"] = [{"name":"register", "lifespan":2}]
		else:
			speech = "Sorry, I meet some errors. Please try again later!"

	if action == "action.viewvideo":
		print("ViewVideo!")
		content = {
			"Type": "ViewVideo",
			"Id": facebook_userId
		}
		r = requests.post("http://localhost/order.php", data=json.dumps(content))
		response = r.json()
		if response.get("Status") == 0:
			speech = "Here is a short video of your front door!"
			facebook = {
  				"facebook": {
    			"attachment": {
      				"type": "video",
      			"payload": {
        			"url": r.json().get('Content').get('url')
      			}
    		}
  			}
			}
			res["data"] = facebook
		elif response.get("Status") == 2:
			speech = "Oh, it seems your are not registered yet. Do you want to register right now?"
			res["contextOut"] = [{"name":"register", "lifespan":2}]
		else:
			speech = "Sorry, I meet some errors. Please try again later!"

	if action == "action.sendalert":
		print("Send Alert!")
		content = {
		"Type": "SendAlert",
		"Id": facebook_userId
		}
		r = requests.post("http://localhost/order.php", data=json.dumps(content))
		response = r.json()
		if response.get("Status") == 0:
			speech = "I have set the beep running!"
		elif response.get("Status") == 2:
			speech = "Oh, it seems your are not registered yet. Do you want to register right now?"
			res["contextOut"] = [{"name":"register", "lifespan":2}]
		else:
			speech = "Sorry, I meet some errors. Please try again later!"
		
	if action == "status.all":
		print("Check current status")
		content = {
		"Type": "HomeStatus",
		"Id": facebook_userId
		}
		r = requests.post("http://localhost/status.php", data=json.dumps(content))
		response = r.json()
		if response.get("Status") == 0:
			speech = "Your home is all right!"
			res["data"] = r.json().get("Content")
		elif response.get("Status") == 2:
			speech = "Oh, it seems your are not registered yet. Do you want to register right now?"
			res["contextOut"] = [{"name":"register", "lifespan":2}]
		else:
			speech = "Sorry, I meet some errors. Please try again later!"

	if action == "action.turnofflights":
		location = parameters.get("Location")
		if location == "":
			content = {
			"Type": "TurnOffLight",
			"Id": facebook_userId
			}
			r = requests.post("http://localhost/order.php", data=json.dumps(content))
			response = r.json()
			if response.get("Status") == 0:
				print("Turn off the lights!")
				speech = "I have turned off the lights!"
			elif response.get("Status") == 2:
				speech = "Oh, it seems your are not registered yet. Do you want to register right now?"
				res["contextOut"] = [{"name":"register", "lifespan":2}]
			else:
				speech = "Sorry, I meet some errors. Please try again later!"
		else:
			content = {
			"Type": "TurnOffLight",
			"Id": facebook_userId,
			"Location": location
			}
			r = requests.post("http://localhost/order.php", data=json.dumps(content))
			response = r.json()
			if response.get("Status") == 0:
				print("Turn off the lights!" + location)
				speech = "I have turned off the lights in the " + location + " !"
			elif response.get("Status") == 2:
				speech = "Oh, it seems your are not registered yet. Do you want to register right now?"
				res["contextOut"] = [{"name":"register", "lifespan":2}]
			else:
				speech = "Sorry, I meet some errors. Please try again later!"

	if action == "action.turnonlights":
		location = parameters.get("Location")
		if location == "":
			content = {
			"Type": "TurnOnLight",
			"Id": facebook_userId
			}
			r = requests.post("http://localhost/order.php", data=json.dumps(content))
			response = r.json()
			if response.get("Status") == 0:
				print("Turn on the lights!")
				speech = "I have turned on the lights!"
			elif response.get("Status") == 2:
				speech = "Oh, it seems your are not registered yet. Do you want to register right now?"
				res["contextOut"] = [{"name":"register", "lifespan":2}]
			else:
				speech = "Sorry, I meet some errors. Please try again later!"
		else:
			content = {
			"Type": "TurnOnLight",
			"Id": facebook_userId,
			"Location": location
			}
			r = requests.post("http://localhost/order.php", data=json.dumps(content))
			response = r.json()
			if response.get("Status") == 0:
				print("Turn on the lights!" + location)
				speech = "I have turned on the lights in the " + location + " !"
			elif response.get("Status") == 2:
				speech = "Oh, it seems your are not registered yet. Do you want to register right now?"
				res["contextOut"] = [{"name":"register", "lifespan":2}]
			else:
				speech = "Sorry, I meet some errors. Please try again later!"

	print("Response:")
	print(speech)

	res["speech"] = speech
	res["displayText"] = speech
	res["source"] = "apiai-onlinestore-shipping"

	return res;

def makeWebhookResult(req):
    if req.get("result").get("action") != "shipping.cost":
        return {}
    result = req.get("result")
    parameters = result.get("parameters")
    zone = parameters.get("shipping-zone")

    cost = {'Europe':100, 'North America':200, 'South America':300, 'Asia':400, 'Africa':500}

    speech = "The cost of shipping to " + zone + " is " + str(cost[zone]) + " euros."

    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        #"data": {},
        # "contextOut": [],
        "source": "apiai-onlinestore-shipping"
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    # logging.basicConfig(level=logging.DEBUG,
    #             format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
    #             datefmt='%a, %d %b %Y %H:%M:%S',
    #             filename='app.log',
    #             filemode='w')
    # logging.debug('This is debug message')
    # logging.info('This is info message')
    # logging.warning('This is warning message')

    print "Starting app on port %d" % port

    app.run(debug=False, port=port, host='0.0.0.0')