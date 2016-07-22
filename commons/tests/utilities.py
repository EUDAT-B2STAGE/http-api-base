import unittest
import random
import json
import string
import logging

from commons.logs import get_logger
from restapi.confs.config import TEST_HOST, SERVER_PORT, API_URL, AUTH_URL
import commons.htmlcodes as hcodes

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)

API_URI = 'http://%s:%s%s' % (TEST_HOST, SERVER_PORT, API_URL)
AUTH_URI = 'http://%s:%s%s' % (TEST_HOST, SERVER_PORT, AUTH_URL)

GET = 'GET'
POST = 'POST'
PUT = 'PUT'
DELETE = 'DELETE'

# Status aliases used to shorten method calls
OK = hcodes.HTTP_OK_BASIC                           # 200
NO_CONTENT = hcodes.HTTP_OK_NORESPONSE              # 204
BAD_REQUEST = hcodes.HTTP_BAD_REQUEST               # 400
UNAUTHORIZED = hcodes.HTTP_BAD_UNAUTHORIZED         # 401
FORBIDDEN = hcodes.HTTP_BAD_FORBIDDEN               # 403
NOTFOUND = hcodes.HTTP_BAD_NOTFOUND                 # 404
NOT_ALLOWED = hcodes.HTTP_BAD_METHOD_NOT_ALLOWED    # 405
CONFLICT = hcodes.HTTP_BAD_CONFLICT                 # 409

# This error is returned by Flask when a method is not implemented [405 status]
NOT_ALLOWED_ERROR = {
    'message': 'The method is not allowed for the requested URL.'
}


class ParsedResponse(object):
    pass


class TestUtilities(unittest.TestCase):

    def save(self, variable, value, read_only=False):
        """
            Save a variable in the class, to be re-used in further tests
            In read_only mode the variable cannot be rewritten
        """
        if hasattr(self.__class__, variable):
            data = getattr(self.__class__, variable)
            if "read_only" in data and data["read_only"]:
                self.assertFalse(
                    "Cannot overwrite a read_only variable [%s]" % variable
                )

        data = {'value': value, 'read_only': read_only}
        setattr(self.__class__, variable, data)

    def get(self, variable):
        """
            Retrieve a previously stored variable using the .save method
        """
        if not hasattr(self.__class__, variable):
            return None

        data = getattr(self.__class__, variable)
        if "value" in data:
            return data["value"]
        return None

    def do_login(self, USER, PWD):
        """
            Make login and return both token and authorization header
        """

        r = self.app.post(AUTH_URI + '/login',
                          data=json.dumps({
                                          'username': USER,
                                          'password': PWD
                                          }))
        self.assertEqual(r.status_code, OK)

        content = json.loads(r.data.decode('utf-8'))

        token = content['Response']['data']['token']
        return {'Authorization': 'Bearer ' + token}, token

    def destroyToken(self, token, headers):
        r = self.app.get(AUTH_URI + '/tokens', headers=headers)
        self.assertEqual(r.status_code, OK)

        content = json.loads(r.data.decode('utf-8'))
        self.assertEqual(r.status_code, OK)

        for data in content['Response']['data']:
            if data["token"] == token:
                id = data["id"]
                uri = '%s/tokensadminonly/%s' % (AUTH_URI, id)
                r = self.app.delete(uri, headers=headers)
                self.assertEqual(r.status_code, NO_CONTENT)
                break

    def get_profile(self, headers):
        r = self.app.get(AUTH_URI + '/profile', headers=headers)
        content = json.loads(r.data.decode('utf-8'))
        return content['Response']['data']

    def randomString(self, len=16, prefix="TEST:"):
        if len > 500000:
            lis = list(string.ascii_lowercase)
            return ''.join(random.choice(lis) for _ in range(len))

        rand = random.SystemRandom()
        charset = string.ascii_uppercase + string.digits

        random_string = prefix
        for _ in range(len):
            random_string += rand.choice(charset)

        return random_string

    def buildData(self, schema):
        """
            Taking as input a json schema returns a dictionary of random data
            expected json schema:
            schema = [
                {
                    "key": "unique-key-name-of-this-field",
                    "type": "text/int/select",
                    "required": "true/false",
                    "options": [
                        {"id": "OptionID", "value": "OptionValue"},
                        ...
                    ]
                },
                ...
            ]
        """
        data = {}
        for d in schema:

            key = d["key"]
            type = d["type"]
            value = None

            if type == "select":
                if len(d["options"]) > 0:
                    value = d["options"][0]["id"]
                else:
                    value = "NOT_FOUND"
            elif type == "int":
                value = random.randrange(0, 1000, 1)
            else:
                value = self.randomString()

            data[key] = value

        return data

    def getPartialData(self, schema, data):
        """
            Following directives contained in the json schema and
            taking as input a pre-built data dictionary, this method
            remove one of the required fields from data
        """
        partialData = data.copy()
        for d in schema:
            if not d['required']:
                continue

            key = d["key"]

            del partialData[key]
            return partialData
        return None

    def parseResponse(self, response, inner=False):
        """
            This method is used to verify and simplify the access to
            json-standard-responses. It returns an Object filled
            with attributes obtained by mapping json content.
            This is a recursive method, the inner flag is used to
            distinguish further calls on inner elements.
        """

        if response is None:
            return None

        # OLD RESPONSE, NOT STANDARD-JSON
        if not inner and isinstance(response, dict):
            return response

        data = []

        self.assertIsInstance(response, list)

        for element in response:
            self.assertIsInstance(element, dict)
            self.assertIn("id", element)
            self.assertIn("type", element)
            self.assertIn("attributes", element)
            # # links is optional -> don't test
            # self.assertIn("links", element)
            # # relationships is optional -> don't test
            # self.assertIn("relationships", element)

            newelement = ParsedResponse()
            setattr(newelement, "_id", element["id"])
            setattr(newelement, "_type", element["type"])
            if "links" in element:
                setattr(newelement, "_links", element["links"])

            setattr(newelement, "attributes", ParsedResponse())

            for key in element["attributes"]:
                setattr(newelement.attributes, key, element["attributes"][key])

            if "relationships" in element:
                for relationship in element["relationships"]:
                    setattr(newelement, "_" + relationship,
                            self.parseResponse(
                                element["relationships"][relationship],
                                inner=True
                            ))

            data.append(newelement)

        return data

    def checkResponse(self, response, fields, relationships):
        """
        Verify that the response contains the given fields and relationships
        """

        for f in fields:
            # How to verify the existence of a property?
            # assertTrue will hide the name of the missing property
            # I can verify my self and then use an always-false assert
            if not hasattr(response[0].attributes, f):
                self.assertIn(f, [])

        for r in relationships:
            if not hasattr(response[0], "_" + r):
                self.assertIn(r, [])

    def _test_endpoint(self, endpoint, headers=None,
                       private_get=None,
                       private_post=None,
                       private_put=None,
                       private_delete=None):

        """
            Makes standard tests on endpoint
            private=False   -> test the method exists
                                    GET -> 200 OK
                                    POST/PUT/DELETE -> 400 BAD REQUEST
            private=True    -> test the method exists and requires a token
                                    no token -> 401 UNAUTHORIZED
                                    with token -> 200 OK / 400 BAD REQUEST
            private=None    -> test the method do not exist -> 405 NOT ALLOWED
        """

        # # # TEST GET # # #
        r = self.app.get(API_URI + '/' + endpoint)
        if private_get is None:
            self.assertEqual(r.status_code, NOT_ALLOWED)
        elif not private_get:
            self.assertEqual(r.status_code, OK)
        else:
            self.assertEqual(r.status_code, UNAUTHORIZED)

            r = self.app.get(API_URI + '/' + endpoint, headers=headers)
            self.assertEqual(r.status_code, OK)

        # # # TEST POST # # #
        r = self.app.post(API_URI + '/' + endpoint)
        if private_post is None:
            self.assertEqual(r.status_code, NOT_ALLOWED)
        elif not private_post:
            self.assertEqual(r.status_code, OK)
        else:
            self.assertEqual(r.status_code, UNAUTHORIZED)

            r = self.app.post(API_URI + '/' + endpoint, headers=headers)
            self.assertEqual(r.status_code, OK)

        # # # TEST PUT # # #
        r = self.app.put(API_URI + '/' + endpoint)
        if private_put is None:
            self.assertEqual(r.status_code, NOT_ALLOWED)
        elif not private_put:
            self.assertEqual(r.status_code, BAD_REQUEST)
        else:
            self.assertEqual(r.status_code, UNAUTHORIZED)

            r = self.app.put(API_URI + '/' + endpoint, headers=headers)
            self.assertEqual(r.status_code, BAD_REQUEST)

        # # # TEST DELETE # # #
        r = self.app.delete(API_URI + '/' + endpoint)
        if private_delete is None:
            self.assertEqual(r.status_code, NOT_ALLOWED)
        elif not private_delete:
            self.assertEqual(r.status_code, BAD_REQUEST)
        else:
            self.assertEqual(r.status_code, UNAUTHORIZED)

            r = self.app.delete(API_URI + '/' + endpoint, headers=headers)
            self.assertEqual(r.status_code, BAD_REQUEST)

    # headers should be optional, if auth is not required
    def _test_method(self, method, endpoint, headers,
                     status, parse_response=False,
                     data=None, error={}):

        """
            Test a method (GET/POST/PUT/DELETE) on a given endpoint
            and verifies status error and optionally the returned error
            (disabled when error=None)
            It returns content['Response']['data']
            when parse_response=True the returned response
            is parsed using self.parseResponse mnethod
        """

        if data is not None:
            data = json.dumps(data)

        URI = API_URI + '/' + endpoint

        if method == GET:
            r = self.app.get(URI, headers=headers)
        elif method == POST:
            r = self.app.post(URI, data=data, headers=headers)
        elif method == PUT:
            r = self.app.put(URI, data=data, headers=headers)
        elif method == DELETE:
            r = self.app.delete(URI, data=data, headers=headers)

        self.assertEqual(r.status_code, status)

        if status == NO_CONTENT:
            return None

        content = json.loads(r.data.decode('utf-8'))

        # In this case the response is returned by Flask
        if status == NOT_ALLOWED:
            self.assertEqual(content, NOT_ALLOWED_ERROR)
            return content

        if error is not None:
            errors = content['Response']['errors']
            if errors is not None:
                self.assertEqual(errors[0], error)

        if parse_response:
            return self.parseResponse(content['Response']['data'])
        return content['Response']['data']

    def _test_get(self, endpoint, headers,
                  status, parse_response=True,
                  error={}):

        return self._test_method(
            GET, endpoint, headers, status,
            parse_response=parse_response, error=error
        )

    def _test_create(self, endpoint, headers, data, status, error={}):

        return self._test_method(
            POST, endpoint, headers, status,
            data=data, error=error
        )

    # headers should be optional, if auth is not required
    def _test_update(self, endpoint, headers, data, status, error={}):

        return self._test_method(
            PUT, endpoint, headers, status,
            data=data, error=error
        )

    # headers should be optional, if auth is not required
    def _test_delete(self, endpoint, headers, status, error={}, data={}):

        return self._test_method(
            DELETE, endpoint, headers, status,
            data=data, error=error
        )

    def _test_troublesome_create(self, endpoint, headers, schema,
                                 status_configuration={},
                                 second_endpoint=None):
        """
            Test several troublesome conditions based on field types
                (obtained from json schema)
            If POST call returns a 200 OK PUT and DELETE are also called

            returned status code can be overwritten by providing a
                status_configuration dictionary, e.g:
                    status_conf = {}
                    status_conf["NEGATIVE_NUMBER"] = BAD_REQUEST
                    status_conf["LONG_NUMBER"] = BAD_REQUEST
        """

        troublesome_tests = {}
        troublesome_tests["EXTERNAL_DOUBLE_QUOTES"] = ["text", OK]
        troublesome_tests["EXTERNAL_SINGLE_QUOTES"] = ["text", OK]
        troublesome_tests["INTERNAL_DOUBLE_QUOTES"] = ["text", OK]
        troublesome_tests["INTERNAL_SINGLE_QUOTES"] = ["text", OK]
        troublesome_tests["INTERNAL_SINGLE_QUOTES"] = ["text", OK]
        troublesome_tests["LONG_TEXT"] = ["text", OK]
        troublesome_tests["VERY_LONG_TEXT"] = ["text", OK]
        # troublesome_tests["EXTREMELY_LONG_TEXT"] = ["text", OK]
        # troublesome_tests["TOOOO_LONG_TEXT"] = ["text", OK]
        troublesome_tests["LETTERS_WITH_ACCENTS"] = ["text", OK]
        troublesome_tests["SPECIAL_CHARACTERS"] = ["text", OK]
        troublesome_tests["EMPTY_STRING"] = ["text", BAD_REQUEST]
        troublesome_tests["NEGATIVE_NUMBER"] = ["int", OK]
        troublesome_tests["ZERO"] = ["int", OK]
        troublesome_tests["LONG_NUMBER"] = ["int", OK]
        troublesome_tests["TOO_LONG_NUMBER"] = ["int", OK]
        troublesome_tests["NOT_A_NUMBER"] = ["int", BAD_REQUEST]
        troublesome_tests["UNEXPECTED_OPTION"] = ["select", BAD_REQUEST]
        data = self.buildData(schema)

        for trouble_type in troublesome_tests:

            t_type = troublesome_tests[trouble_type][0]
            if trouble_type in status_configuration:
                t_status = status_configuration[trouble_type]
                post_status = t_status
                put_status = t_status
            else:
                t_status = troublesome_tests[trouble_type][1]
                post_status = t_status
                put_status = t_status
                if put_status == OK:
                    put_status = NO_CONTENT

            post_data = data.copy()
            put_data = data.copy()
            t_found = False

            for s in schema:
                if s["type"] != t_type:
                    continue

                field_key = s["key"]
                trouble = self.applyTroubles(data[field_key], trouble_type)
                post_data[field_key] = trouble
                put_data[field_key] = trouble
                t_found = True

            if not t_found:
                print(
                    "\t *** SKIPPING TEST %s - type %s not found" %
                    (trouble_type, t_type))
                continue

            print("\t *** TESTING %s " % trouble_type)

            id = self._test_create(
                endpoint, headers, post_data, post_status, error=None)

            if post_status != OK:
                continue

            if id is None:
                continue

            if second_endpoint is None:
                tmp_ep = "%s/%s" % (endpoint, id)
            else:
                tmp_ep = "%s/%s" % (second_endpoint, id)

            self._test_update(
                tmp_ep, headers, put_data, put_status, error=None)

            self._test_delete(tmp_ep, headers, NO_CONTENT)

    def applyTroubles(self, data, trouble_type):
        """
            Applies one of known troublesome conditions to a prefilled data.
            Returned value can contain or not the original data, depending
                on the specific trouble type
        """

        if trouble_type == 'EMPTY_STRING':
            return ""
        if trouble_type == 'NEGATIVE_NUMBER':
            return -42
        if trouble_type == 'ZERO':
            return 0
        if trouble_type == 'LONG_NUMBER':
            return 2147483648
        if trouble_type == 'TOO_LONG_NUMBER':
            return 18446744073709551616
        if trouble_type == 'NOT_A_NUMBER':
            return "THIS_IS_NOT_A_NUMBER"

        if isinstance(data, str):
            strlen = len(data)
            halflen = int(strlen / 2)
            prefix = data[:halflen]
            suffix = data[halflen:]

            if trouble_type == 'EXTERNAL_DOUBLE_QUOTES':
                return '%s%s%s' % ("\"", data, "\"")
            if trouble_type == 'EXTERNAL_SINGLE_QUOTES':
                return '%s%s%s' % ("\'", data, "\'")
            if trouble_type == 'INTERNAL_DOUBLE_QUOTES':
                return '%s%s%s' % ("PRE_\"", data, "\"_POST")
            if trouble_type == 'INTERNAL_SINGLE_QUOTES':
                return '%s%s%s' % ("PRE_\'", data, "\'_POST")
            if trouble_type == 'LETTERS_WITH_ACCENTS':
                return '%s%s%s' % (prefix, "àèìòùé", suffix)
            if trouble_type == 'SPECIAL_CHARACTERS':
                return '%s%s%s' % (prefix, "૱꠸┯┰┱┲❗►◄ĂăǕǖꞀ¤Ð¢℥Ω℧Kℶℷℸⅇ⅊⚌⚍⚎⚏⚭⚮⌀⏑⏒⏓⏔⏕⏖⏗⏘⏙⏠⏡⏦ᶀᶁᶂᶃᶄᶆᶇᶈᶉᶊᶋᶌᶍᶎᶏᶐᶑᶒᶓᶔᶕᶖᶗᶘᶙᶚᶸᵯᵰᵴᵶᵹᵼᵽᵾᵿ  ‌‍‎‏ ⁁⁊ ⁪⁫⁬⁭⁮⁯⸜⸝¶¥£⅕⅙⅛⅔⅖⅗⅘⅜⅚⅐⅝↉⅓⅑⅒⅞←↑→↓↔↕↖↗↘↙↚↛↜↝↞↟↠↡↢↣↤↥↦↧↨↩↪↫↬↭↮↯↰↱↲↳↴↵↶↷↸↹↺↻↼↽↾↿⇀⇁⇂⇃⇄⇅⇆⇇⇈⇉⇊⇋⇌⇍⇎⇏⇐⇑⇒⇓⇔⇕⇖⇗⇘⇙⇚⇛⇜⇝⇞⇟⇠⇡⇢⇣⇤⇥⇦⇨⇩⇪⇧⇫⇬⇭⇮⇯⇰⇱⇲⇳⇴⇵⇶⇷⇸⇹⇺⇻⇼⇽⇾⇿⟰⟱⟲⟳⟴⟵⟶⟷⟸⟹⟺⟻⟼⟽⟾⟿⤀⤁⤂⤃⤄⤅⤆⤇⤈⤉⤊⤋⤌⤍⤎⤏⤐⤑⤒⤓⤔⤕⤖⤗⤘⤙⤚⤛⤜⤝⤞⤟⤠⤡⤢⤣⤤⤥⤦⤧⤨⤩⤪⤫⤬⤭⤮⤯⤰⤱⤲⤳⤴⤵⤶⤷⤸⤹⤺⤻⤼⤽⤾⤿⥀⥁⥂⥃⥄⥅⥆⥇⥈⥉⥊⥋⥌⥍⥎⥏⥐⥑⥒⥓⥔⥕⥖⥗⥘⥙⥚⥛⥜⥝⥞⥟⥠⥡⥢⥣⥤⥥⥦⥧⥨⥩⥪⥫⥬⥭⥮⥯⥰⥱⥲⥳⥴⥵⥶⥷⥸⥹⥺⥻⥼⥽⥾⥿➔➘➙➚➛➜➝➞➝➞➟➠➡➢➣➤➥➦➧➨➩➩➪➫➬➭➮➯➱➲➳➴➵➶➷➸➹➺➻➼➽➾⬀⬁⬂⬃⬄⬅⬆⬇⬈⬉⬊⬋⬌⬍⬎⬏⬐⬑☇☈⏎⍃⍄⍅⍆⍇⍈⍐⍗⍌⍓⍍⍔⍏⍖♾⎌☊☋☌☍⌃⌄⌤⌅⌆⌇⚋⚊⌌⌍⌎⌏⌐⌑⌔⌕⌗⌙⌢⌣⌯⌬⌭⌮⌖⌰⌱⌲⌳⌴⌵⌶⌷⌸⌹⌺⌻⌼⍯⍰⌽⌾⌿⍀⍁⍂⍉⍊⍋⍎⍏⍑⍒⍕⍖⍘⍙⍚⍛⍜⍝⍞⍠⍟⍡⍢⍣⍤⍥⍨⍩⍦⍧⍬⍿⍪⍮⍫⍱⍲⍭⍳⍴⍵⍶⍷⍸⍹⍺⍼⍽⍾⎀⎁⎂⎃⎄⎅⎆⎉⎊⎋⎍⎎⎏⎐⎑⎒⎓⎔⎕⏣⌓⏥⏢⎖⎲⎳⎴⎵⎶⎸⎹⎺⎻⎼⎽⎾⎿⏀⏁⏂⏃⏄⏅⏆⏇⏈⏉⏉⏋⏌⏍⏐⏤⏚⏛Ⓝℰⓦ!   ⌘«»‹›‘’“”„‚❝❞£¥€$¢¬¶@§®©™°×π±√‰Ω∞≈÷~≠¹²³½¼¾‐–—|⁄\[]{}†‡…·•●⌥⌃⇧↩¡¿‽⁂∴∵◊※←→↑↓☜☞☝☟✔★☆♺☼☂☺☹☃✉✿✄✈✌✎♠♦♣♥♪♫♯♀♂αßÁáÀàÅåÄäÆæÇçÉéÈèÊêÍíÌìÎîÑñÓóÒòÔôÖöØøÚúÙùÜüŽž₳฿￠€₡¢₢₵₫￡£₤₣ƒ₲₭₥₦₱＄$₮₩￦¥￥₴₰¤៛₪₯₠₧₨௹﷼㍐৲৳~ƻƼƽ¹¸¬¨ɂǁ¯Ɂǂ¡´°ꟾ¦}{|.,·])[/_\¿º§\"*-+(!&%$¼¾½¶©®@ẟⱿ`Ȿ^꜠꜡ỻ'=:;<ꞌꞋ꞊ꞁꞈ꞉>?÷ℾℿ℔℩℉⅀℈þðÞµªꝋꜿꜾⱽⱺⱹⱷⱶⱵⱴⱱⱰⱦȶȴȣȢȡȝȜțȋȊȉȈǯǮǃǀƿƾƺƹƸƷƲưƪƣƢƟƛƖƕƍſỽ⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸔⸕▲▼◀▶◢◣◥◤△▽◿◺◹◸▴▾◂▸▵▿◃▹◁▷◅▻◬⟁⧋⧊⊿∆∇◭◮⧩⧨⌔⟐◇◆◈⬖⬗⬘⬙⬠⬡⎔⋄◊⧫⬢⬣▰▪◼▮◾▗▖■∎▃▄▅▆▇█▌▐▍▎▉▊▋❘❙❚▀▘▝▙▚▛▜▟▞░▒▓▂▁▬▔▫▯▭▱◽□◻▢⊞⊡⊟⊠▣▤▥▦⬚▧▨▩⬓◧⬒◨◩◪⬔⬕❏❐❑❒⧈◰◱◳◲◫⧇⧅⧄⍁⍂⟡⧉○◌◍◎◯❍◉⦾⊙⦿⊜⊖⊘⊚⊛⊝●⚫⦁◐◑◒◓◔◕⦶⦸◵◴◶◷⊕⊗⦇⦈⦉⦊❨❩⸨⸩◖◗❪❫❮❯❬❭❰❱⊏⊐⊑⊒◘◙◚◛◜◝◞◟◠◡⋒⋓⋐⋑╰╮╭╯⌒╳✕╱╲⧸⧹⌓◦❖✖✚✜⧓⧗⧑⧒⧖_⚊╴╼╾‐⁃‑‒-–⎯—―╶╺╸─━┄┅┈┉╌╍═≣≡☰☱☲☳☴☵☶☷╵╷╹╻│▕▏┃┆┇┊╎┋╿╽┌┍┎┏┐┑┒┓└┕┖┗┘┙┚┛├┝┞┟┠┡┢┣┤┥┦┧┨┩┪┫┬┭┮┳┴┵┶┷┸┹┺┻┼┽┾┿╀╁╂╃╄╅╆╇╈╉╊╋╏║╔╒╓╕╖╗╚╘╙╛╜╝╞╟╠╡╢╣╤╥╦╧╨╩╪╫╬⌞⌟⌜⌝⌊⌋⌉⌈⌋₯ἀἁἂἃἄἅἆἇἈἉἊἋἌἍἎἏἐἑἒἓἔἕἘἙἚἛἜἝἠἡἢἣἤἥἦἧἨἩἪἫἬἭἮἯἰἱἲἳἴἵἶἷἸἹἺἻἼἽἾἿὀὁὂὃὄὅὈὉὊὋὌὍὐὑὒὓὔὕὖὗὙὛὝὟὠὡὢὣὤὥὦὧὨὩὪὫὬὭὮὯὰάὲέὴήὶίὸόὺύὼώᾀᾁᾂᾃᾄᾅᾆᾇᾈᾉᾊᾋᾌᾍᾎᾏᾐᾑᾒᾓᾔᾕᾖᾗᾘᾙᾚᾛᾜᾝᾞᾟᾠᾡᾢᾣᾤᾥᾦᾧᾨᾩᾪᾫᾬᾭᾮᾯᾰᾱᾲᾳᾴᾶᾷᾸᾹᾺΆᾼ᾽ι᾿῀῁ῂῃῄῆῇῈΈῊΉῌ῍῎῏ῐῑῒΐῖῗῘῙῚΊ῝῞῟ῠῡῢΰῤῥῦῧῨῩῪΎῬ῭΅`ῲῳῴῶῷῸΌῺΏῼ´῾ͰͱͲͳʹ͵Ͷͷͺͻͼͽ;΄΅Ά·ΈΉΊΌΎΏΐΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩΪΫάέήίΰαβγδεζηθικλμνξοπρςστυφχψωϊϋόύώϐϑϒϓϔϕϖϗϘϙϚϛϜϝϞϟϠϡϢϣϤϥϦϧϨϩϪϫϬϭϮϯϰϱϲϳϴϵ϶ϷϸϹϺϻϼϽϾϿⒶⓐ⒜AaẠạẢảḀḁÂÃǍǎẤấẦầẨẩȂȃẪẫẬậÀÁẮắẰằẲẳẴẵẶặĀāĄąǞȀȁÅǺǻÄäǟǠǡâáåãàẚȦȧȺÅⱥÆæǼǢǣⱯꜲꜳꜸꜺⱭꜹꜻª℀⅍℁Ⓑⓑ⒝BbḂḃḄḅḆḇƁɃƀƃƂƄƅℬⒸⓒ⒞CcḈḉĆćĈĉĊċČčÇçƇƈȻȼℂ℃ℭƆ℅℆℄ꜾꜿⒹⓓ⒟DdḊḋḌḍḎḏḐḑḒḓĎďƊƋƌƉĐđȡⅅⅆǱǲǳǄǅǆȸⒺⓔ⒠EeḔḕḖḗḘḙḚḛḜḝẸẹẺẻẾếẼẽỀềỂểỄễỆệĒēĔĕĖėĘęĚěÈèÉéÊêËëȄȅȨȩȆȇƎⱸɆℇℯ℮ƐℰƏǝⱻɇⒻⓕ⒡FfḞḟƑƒꜰℲⅎꟻℱ℻Ⓖⓖ⒢GgƓḠḡĜĝĞğĠġĢģǤǥǦǧǴℊ⅁ǵⒽⓗ⒣HhḢḣḤḥḦḧḨḩḪḫẖĤĥȞȟĦħⱧⱨꜦℍǶℏℎℋℌꜧⒾⓘ⒤IiḬḭḮḯĲĳìíîïÌÍÎÏĨĩĪīĬĭĮįıƗƚỺǏǐⅈⅉℹℑℐⒿⓙ⒥JjĴĵȷⱼɈɉǰⓀⓚ⒦KkḰḱḲḳḴḵĶķƘƙꝀꝁꝂꝃꝄꝅǨǩⱩⱪĸⓁⓛ⒧LlḶḷḸḹḺḻḼḽĹĺĻļĽİľĿŀŁłỈỉỊịȽⱠꝈꝉⱡⱢꞁℒǇǈǉ⅃⅂ℓȉȈȊȋⓂⓜ⒨MmḾḿṀṁṂṃꟿꟽⱮƩƜℳⓃⓝ⒩NnṄṅṆṇṈṉṊṋŃńŅņŇňǸǹŊƝñŉÑȠƞŋǊǋǌȵℕ№OoṌṍṎṏṐṑṒṓȪȫȬȭȮȯȰȱǪǫǬǭỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợƠơŌōŎŏŐőÒÓÔÕÖǑȌȍȎȏŒœØǾꝊǽǿℴ⍥⍤Ⓞⓞ⒪òóôõöǒøꝎꝏⓅⓟ⒫℗PpṔṕṖṗƤƥⱣℙǷꟼ℘Ⓠⓠ⒬QqɊɋℚ℺ȹⓇⓡ⒭RrŔŕŖŗŘřṘṙṚṛṜṝṞṟȐȑȒȓɍɌƦⱤ℞Ꝛꝛℜℛ℟ℝⓈⓢ⒮SsṠṡṢṣṤṥṦṧṨṩŚśŜŝŞşŠšȘșȿꜱƧƨẞßẛẜẝ℠Ⓣⓣ⒯TtṪṫṬṭṮṯṰṱŢţŤťŦŧƬƮẗȚȾƫƭțⱦȶ℡™Ⓤⓤ⒰UuṲṳṴṵṶṷṸṹṺṻỤỦủỨỪụứỬửừữỮỰựŨũŪūŬŭŮůŰűǙǚǗǘǛǜŲųǓǔȔȕÛûȖȗÙùÜüƯúɄưƲƱⓋⓥ⒱VvṼṽṾṿỼɅ℣ⱱⱴⱽⓌⓦ⒲WwẀẁẂẃẄẅẆẇẈẉŴŵẘⱲⱳⓍⓧ⒳XxẊẋẌẍℵ×Ⓨⓨ⒴yYẎẏỾỿẙỲỳỴỵỶỷỸỹŶŷƳƴŸÿÝýɎɏȲƔ⅄ȳℽⓏⓩ⒵ZzẐẑẒẓẔẕŹźŻżŽžȤȥⱫⱬƵƶɀℨℤ⟀⟁⟂⟃⟄⟇⟈⟉⟊⟐⟑⟒⟓⟔⟕⟖⟗⟘⟙⟚⟛⟜⟝⟞⟟⟠⟡⟢⟣⟤⟥⟦⟧⟨⟩⟪⟫⦀⦁⦂⦃⦄⦅⦆⦇⦈⦉⦊⦋⦌⦍⦎⦏⦐⦑⦒⦓⦔⦕⦖⦗⦘⦙⦚⦛⦜⦝⦞⦟⦠⦡⦢⦣⦤⦥⦦⦧⦨⦩⦪⦫⦬⦭⦮⦯⦰⦱⦲⦳⦴⦵⦶⦷⦸⦹⦺⦻⦼⦽⦾⦿⧀⧁⧂⧃⧄⧅⧆⧇⧈⧉⧊⧋⧌⧍⧎⧏⧐⧑⧒⧓⧔⧕⧖⧗⧘⧙⧚⧛⧜⧝⧞⧟⧡⧢⧣⧤⧥⧦⧧⧨⧩⧪⧫⧬⧭⧮⧯⧰⧱⧲⧳⧴⧵⧶⧷⧸⧹⧺⧻⧼⧽⧾⧿∀∁∂∃∄∅∆∇∈∉∊∋∌∍∎∏∐∑−∓∔∕∖∗∘∙√∛∜∝∞∟∠∡∢∣∤∥∦∧∨∩∪∫∬∭∮∯∰∱∲∳∴∵∶∷∸∹∺∻∼∽∾∿≀≁≂≃≄≅≆≇≈≉≊≋≌≍≎≏≐≑≒≓≔≕≖≗≘≙≚≛≜≝≞≟≠≡≢≣≤≥≦≧≨≩≪≫≬≭≮≯≰≱≲≳≴≵≶≷≸≹≺≻≼≽≾≿⊀⊁⊂⊃⊄⊅⊆⊇⊈⊉⊊⊋⊌⊍⊎⊏⊐⊑⊒⊓⊔⊕⊖⊗⊘⊙⊚⊛⊜⊝⊞⊟⊠⊡⊢⊣⊤⊥⊦⊧⊨⊩⊪⊫⊬⊭⊮⊯⊰⊱⊲⊳⊴⊵⊶⊷⊸⊹⊺⊻⊼⊽⊾⊿⋀⋁⋂⋃⋄⋅⋆⋇⋈⋉⋊⋋⋌⋍⋎⋏⋐⋑⋒⋓⋔⋕⋖⋗⋘⋙⋚⋛⋜⋝⋞⋟⋠⋡⋢⋣⋤⋥⋦⋧⋨⋩⋪⋫⋬⋭⋮⋯⋰⋱⋲⋳⋴⋵⋶⋷⋸⋹⋺⋻⋼⋽⋾⋿✕✖✚◀▶❝❞★☆☼☂☺☹✄✈✌✎♪♫☀☁☔⚡❆☽☾✆✔☯☮☠⚑☬✄✏♰✡✰✺⚢⚣♕♛♚♬ⓐⓑⓒⓓ↺↻⇖⇗⇘⇙⟵⟷⟶⤴⤵⤶⤷➫➬€₤＄₩₪⟁⟐◆⎔░▢⊡▩⟡◎◵⊗❖ΩβΦΣΞ⟁⦻⧉⧭⧴∞≌⊕⋍⋰⋱✖⓵⓶⓷⓸⓹⓺⓻⓼⓽⓾ᴕ⸨⸩❪❫⓵⓶⓷⓸⓹⓺⓻⓼⓽⓾⒈⒉⒊⒋⒌⒍⒎⒏⒐⒑⒒⒓⒔⒕⒖⒗⒘⒙⒚⒛⓪①②③④⑤⑥⑦⑧⑨⑩➀➁➂➃➄➅➆➇➈➉⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳⓿❶❷❸❹❺❻❼❽❾❿➊➋➌➍➎➏➐➑➒➓⓫⓬⓭⓮⓯⓰⓱⓲⓳⓴⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽⑾⑿⒀⒁⒂⒃⒄⒅⒆⒇ᶅᶛᶜᶝᶞᶟᶠᶡᶢᶣᶤᶥᶦᶧᶨᶩᶪᶫᶬᶭᶮᶯᶰᶱᶲᶳᶴᶵᶶᶷᶹᶺᶻᶼᶽᶾᶿᴀᴁᴂᴃᴄᴅᴆᴇᴈᴉᴊᴋᴌᴍᴎᴏᴐᴑᴒᴓᴔᴕᴖᴗᴘᴙᴚᴛᴜᴝᴞᴟᴠᴡᴢᴣᴤᴥᴦᴧᴨᴩᴪᴫᴬᴭᴮᴯᴰᴱᴲᴳᴴᴵᴶᴷᴸᴹᴺᴻᴼᴽᴾᴿᵀᵁᵂᵃᵄᵅᵆᵇᵈᵉᵊᵋᵌᵍᵎᵏᵐᵑᵒᵓᵔᵕᵖᵗᵘᵙᵚᵛᵜᵝᵞᵟᵠᵡᵢᵣᵤᵥᵦᵧᵨᵩᵪᵫᵬᵭᵮᵱᵲᵳᵵᵷᵸᵺᵻ᷎᷏᷋᷌ᷓᷔᷕᷖᷗᷘᷙᷛᷜᷝᷞᷟᷠᷡᷢᷣᷤᷥᷦ᷍‘’‛‚“”„‟«»‹›Ꞌ❛❜❝❞<>@‧¨․꞉:⁚⁝⁞‥…⁖⸪⸬⸫⸭⁛⁘⁙⁏;⦂⁃‐‑‒-–⎯—―_⁓⸛⸞⸟ⸯ¬/\⁄\⁄|⎜¦‖‗†‡·•⸰°‣⁒%‰‱&⅋§÷+±=꞊′″‴⁗‵‶‷‸*⁑⁎⁕※⁜⁂!‼¡?¿⸮⁇⁉⁈‽⸘¼½¾²³©®™℠℻℅℁⅍℄¶⁋❡⁌⁍⸖⸗⸚⸓()[]{}⸨⸩❨❩❪❫⸦⸧❬❭❮❯❰❱❴❵❲❳⦗⦘⁅⁆〈〉⏜⏝⏞⏟⸡⸠⸢⸣⸤⸥⎡⎤⎣⎦⎨⎬⌠⌡⎛⎠⎝⎞⁀⁔‿⁐‾⎟⎢⎥⎪ꞁ⎮⎧⎫⎩⎭⎰⎱✈☀☼☁☂☔⚡❄❅❆☃☉☄★☆☽☾⌛⌚☇☈⌂⌁✆☎☏☑✓✔⎷⍻✖✗✘☒✕☓☕♿✌☚☛☜☝☞☟☹☺☻☯⚘☮✝⚰⚱⚠☠☢⚔⚓⎈⚒⚑⚐☡❂⚕⚖⚗✇☣⚙☤⚚⚛⚜☥☦☧☨☩†☪☫☬☭✁✂✃✄✍✎✏✐✑✒✉✙✚✜✛♰♱✞✟✠✡☸✢✣✤✥✦✧✩✪✫✬✭✮✯✰✲✱✳✴✵✶✷✸✹✺✻✼✽✾❀✿❁❃❇❈❉❊❋⁕☘❦❧☙❢❣♀♂⚢⚣⚤⚦⚧⚨⚩☿♁⚯♔♕♖♗♘♙♚♛♜♝♞♟☖☗♠♣♦♥❤❥♡♢♤♧⚀⚁⚂⚃⚄⚅⚇⚆⚈⚉♨♩♪♫♬♭♮♯⌨⏏⎗⎘⎙⎚⌥⎇⌘⌦⌫⌧♲♳♴♵♶♷♸♹♺♻♼♽⁌⁍⎌⌇⌲⍝⍟⍣⍤⍥⍨⍩⎋♃♄♅♆♇♈♉♊♋♌♍♎♏♐♑♒♓⏚⏛​|",suffix)
            if trouble_type == 'LONG_TEXT':
                return '%s%s%s' % (prefix, self.randomString(len=256, prefix=""), suffix)
            if trouble_type == 'VERY_LONG_TEXT':
                return '%s%s%s' % (prefix, self.randomString(len=65536, prefix=""), suffix) 
            if trouble_type == 'EXTREMELY_LONG_TEXT':
                return '%s%s%s' % (prefix, self.randomString(len=16777216, prefix=""), suffix)
            if trouble_type == 'TOOOO_LONG_TEXT':
                return '%s%s%s' % (prefix, self.randomString(len=4294967296, prefix=""), suffix)

        if trouble_type == 'UNEXPECTED_OPTION':
            return self.randomString()

        self.assertFalse("Unexpected trouble: %s" % trouble_type)
        return data
