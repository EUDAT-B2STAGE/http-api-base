## Utilities to write tests ##

This collection of utilities is meant to simplify the writing of endpoints tests with the assumption that the endpoints following some conventions:

- endpoints accepting POST data should provide a json schema to describe the required information

            schema = [
                {
                    "key": "unique-key-name-of-this-field",
                    "type": "text/int",
                    "required": "true/false",
                },
                {
                    "key": "unique-key-name-of-this-field",
                    "type": "select",
                    "required": "true/false",
                    "options": [
                        {"id": "OptionID", "value": "OptionValue"},
                        ...
                    ]
                },
                ...
            ]

- endpoints should return responses using a standard json as describe in http://jsonapi.org
- endpoint should accept GET/POST/PUT and DELETE calls with no parameters and return respectively 200 400 400 400 status codes
- POST endpoints when successfull should return and created entity id. This id should be valid for further PUT and DELETE calls 
- PUT and DELETE endpoints should respond on the same endpoints of POST method with the addition of the entity id, e.g.:
	- POST /api/myendpoint
	- PUT /api/myendpoint/_id_
	- DELETE /api/myendpoint/_id_
- Successfully should returns 200 OK (if GET or POST) and 204 NO CONTENT (if PUT and DELETE)

	

## How to use the Test Utilities ##

Your own test class should import and extend test utilities


	from commons.tests.utilities import TestUtilities


		class YourTests(TestUtilities):
			pass


### Save variables and re-use it in other tests of your class

	my_var = 'usefull information'
	self.save("my-variable", my_var)
	...
	previous_info = self.get("my-variable")
	
### Make login and save tokens and headers for further calls

	from restapi.confs.config import USER, PWD
	headers, token = self.do_login(USER, PWD)
	self.save("headers", headers)
	self.save("token", token)
	
### Make basic test on endpoints

	self._test_endpoint(
		your_endpoint,
		headers=headers,
		private_get=False,
		private_post=True,
		private_put=None,
		private_delete=True
	)
	
- private=False -> test if the method exists
	- GET -> 200 OK
	- POST/PUT/DELETE -> 400 BAD REQUEST
- private=True    -> test if the method exists and requires a token
	- no token -> 401 UNAUTHORIZED
	- with token -> 200 OK / 400 BAD REQUEST
- private=None    -> test if the method do not exist
	- all methods -> 405 NOT ALLOWED

In the previous example GET is tested as public, POST and DELETE as private and PUT as not implemented.
Expected returned status code are
- GET: 200
- POST: 401 wihout token and 400 with token
- PUT: 405 
- DELETE: 401 wihout token and 400 with token
 
### Build random data to test POST and PUT endpoints

Your APIs should return a json schema as described above. Once you obtained the json schema you can build random data by using the buildData utility

	data = self.buildData(schema)
	
To test endpoint behaviours when receiving partial data you can use the getPartialData utility

	partial_data = self.buildData(schema, data)
	
This method takes as input both json schema and built data and remove one of the required fields

