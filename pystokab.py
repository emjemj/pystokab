import requests
import time

class StokabAPIClient:

    def __init__(self, client_id, scopes, secret, url):
        self.client_id = client_id
        self.scopes = scopes
        self.secret = secret
        self.url = url

        self.acquire_token()

    def acquire_token(self):
        """ Acquire token from API to allow further use """
        login = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'scope': ' '.join(self.scopes),
            'client_secret': self.secret
        }

        resp = self.post(path='/connect/token', data=login, authenticate=False)

        data = resp.json()
        self.token_acquired = int(time.time())
        self.token_type = data['token_type']
        self.token_ttl = data['expires_in']
        self.token = data['access_token']

    def post(self, path, data=None, json=None, authenticate=True):
        """ Send POST request to API server """

        params = {
            'url': '{}{}'.format(self.url, path),
        }

        if authenticate:
            # Should only be disabled by acquire_token
            params['headers'] = self._authorization_headers()
        if data:
            params['data'] = data
        if json:
            params['json'] = json

        return requests.post(**params)

    def get(self, path, params=None):
        args = {
            'url': '{}{}'.format(self.url, path),
            'headers': self._authorization_headers()
        }

        if params:
            args['params'] = params

        return requests.get(**args)

    def _authorization_headers(self):
        """ Neatly format dict with authorization headers for authenticated api calls """
        return { 'Authorization': '{} {}'.format(self.token_type, self.token) }

    def get_point(self, point_id):
        return Point(apiclient=self, point_id=point_id)

class SimpleDataEntity:

    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        return self.data[key]

class Address(SimpleDataEntity):
    """ Descries a street address """

    def __init__(self, data):
        SimpleDataEntity.__init__(self, data)

class PointInfo(SimpleDataEntity):
    """ Describes point connectivity """

    def __init__(self, data):
        SimpleDataEntity.__init__(self, data)

class RealEstate(SimpleDataEntity):
    """ Describes a realestate """

    def __init(self, data):
        SimpleDataEntity.__init__(self, data)

class Coordinates:
    """ Describes a set of coordinates """

    def __init__(self, data):

        import pyproj

        projections = {
                'RT90_2.5_GON_V_0:-15': 'epsg:3021'
        }

        source = pyproj.Proj(projections[data['projection']])
        dest = pyproj.Proj('epsg:4326')
        res = pyproj.transform(source, dest, data['latitude'], data['longitude'])

        self.latitude = res[0]
        self.longitude = res[1]

    def url(self):

        return 'https://google.com/maps/?q={},{}'.format(self.latitude, self.longitude)

class Point:
    """ Describes a point in the Stokab fiber network """

    TYPE_HOUSENODE = 5
    TYPE_NEUTRAL = 12
    TYPE_COMMERCIAL_HOUSENODE = 14

    def __init__(self, apiclient, point_id, data=None):
        self.apiclient = apiclient
        self.point_id = point_id

        if not data:
            self.data = self.load_data()
        else:
            self.data = data

        self.initialize()

    def load_data(self):
        resp = self.apiclient.get(path='/api/1.3/availability/getByPointId', params={ 'pointId': self.point_id })
        return resp.json()[0]

    def initialize(self):
        """ Initialize internal data structure """
        self.address = Address(self.data['address'])
        self.realestate = RealEstate(self.data['realEstate'])
        self.coordinates = Coordinates(self.data['coordinates'])
        self.district = self.data['district']
        self.city_area = self.data['cityArea']
        self.fiber_status = self.data['fiberStatus']
        self.related_points = []

        for related in self.data['relatedPointIds']:
            obj = Point(related['name'])

        self.point_info = PointInfo(self.data['pointInfo'])

        print(self.point_info.aNode, self.point_info.oNode)
