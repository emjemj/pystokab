import requests
import time

class StokabAPIException(Exception):
    pass

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
        """ Fetch a point specified by its id """
        return Point(apiclient=self, point_id=point_id)

    def get_points_by_realestate(self, realestate, estatesuffix=""):
        """ Find points by realestate """
        resp = self.get(path='/api/1.3/availability/getByEstate',
                        params={'realestate': realestate.upper(), 'estatesuffix': estatesuffix })

        return self.initialize_points(resp.json())

    def get_points_by_address(self, city, street, number, littera=None):
        """ Find points by street address """

        params = {
            'city': city,
            'street': street,
            'number': number,
        }

        if littera:
            params['littera'] = littera

        resp = self.get(path='/api/1.3/availability/getByAddress', params=params)

        return self.initialize_points(resp.json())

    def initialize_points(self, response):
        if 'message' in response:
            raise StokabAPIException(data['message'])

        points = []
        for point in response:
            p = Point(apiclient=self, point_id=point['pointId'], data=point)
            points.append(p)

        return points

    def get_framework_agreements(self):
        """ Get a list of framework agreements """

        resp = self.get(path='/api/1.3/frameworkAgreement')

        agreements = []

        for agreement in resp.json():
            agreements.append(FrameworkAgreement(data=agreement))

        return agreements

    def get_invoice_groups(self):
        """ Get a list of invoice groups """

        resp = self.get(path='/api/1.3/invoiceGroup')

        groups = []

        for group in resp.json():
            groups.append(InvoiceGroup(data=group))

        return groups

    def estimate(self, invoice_group_id, framework_agreement_id, from_point, to_point, customer_type, years, singles=0, pairs=0):
        args = {
            'invoiceGroupId': invoice_group_id,
            'frameworkAgreementId': framework_agreement_id,
            'from': { 'pointId': from_point },
            'to': { 'pointId': to_point },
            'customerType': customer_type,
            'contractPeriodYears': years,
            'noOfSingleFibers': singles,
            'noOfFiberPairs': pairs
        }

        resp = self.post(path='/api/1.3/priceEstimate', json=args)


        data = resp.json()[0]['products']


        products = []

        for product in data:
            products.append(Product(product))

        return ProductList(products)

class ProductList:

    def __init__(self, products=[]):
        self.products = products

    def __iter__(self):
        for product in self.products:
            yield product

    def cheapest(self):
        """ Find cheapest product """
        cheapest = None
        for product in self.products:

            if not cheapest or product.total() < cheapest.total():
                cheapest = product
        return cheapest


class Product:
    """ Product """

    def __init__(self, data):
        self.product_id = data['productId']
        self.name = data['name']
        self.product_type = data['productType']
        self.comment = data['comment']
        self.price = Price(data['price'])

    def total(self):
        return self.price.total()

class Price:
    """ Price """

    def __init__(self, data):
        self.contract_period = data['contractPeriodYears']
        self.otc = data['oneTimeFee']
        self.mrc = data['monthlyFee']

    def total(self):
        """ Calculate total cost over the contract period """
        return self.otc + (self.mrc * (self.contract_period * 12))

    def spec(self):
        """ Return a tuple containing otc and mrc """
        return self.otc, self.mrc


class InvoiceGroup:
    """ Invoicegroup """

    def __init__(self, data):
        self.name = data['name']
        self.client_number = data['clientNumber']
        self.id = data['invoiceGroupId']
        self.number = data['invoiceGroupNumber']

class FrameworkAgreement:
    """ Framework agreement (ramavtal) """

    def __init__(self, data):
        self.agreement_id = data['frameworkAgreementId']
        self.name = data['name']
        self.standard = data['isStandard']
        self.system_id = data['masterSystemId']

class SimpleDataEntity:

    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        return self.data[key]

    def debug(self, indent=False):
        fmt = '{}: {}'
        if indent:
            fmt = '\t{}: {}'

        for key in self.data:
            print(fmt.format(key, self.data[key]))

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
                'RT90_2.5_GON_V_0:-15': 'epsg:3021',
                'SWEREF99 TM': 'epsg:3021',
        }

        source = pyproj.Proj(projections[data['projection']])
        dest = pyproj.Proj('epsg:4326')
        res = pyproj.transform(source, dest, data['latitude'], data['longitude'])

        self.latitude = res[0]
        self.longitude = res[1]

    def url(self):
        """ generate google maps url for the coordinates """

        return 'https://google.com/maps/?q={},{}'.format(self.latitude, self.longitude)

    def debug(self, indent=True):
        if indent:
            print('\t{}'.format(self.url()))
        else:
            print(self.url())

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
            obj = Point(apiclient=self.apiclient, point_id=related['name'])
            self.related_points.append(obj)

        self.point_info = PointInfo(self.data['pointInfo'])

    def debug(self):
        print("--------------------------------------------------------")
        print(self.point_id)
        print("Address")
        self.address.debug(indent=True)
        print("Realestate")
        self.realestate.debug(indent=True)
        print("Coordinates")
        self.coordinates.debug(indent=True)
        print("District: {}".format(self.district))
        print("City area: {}".format(self.city_area))
        print("Fiber status: {}".format(self.fiber_status))
        print("Point Info")
        self.point_info.debug(indent=True)
        print("Related points: {}".format([x.point_id for x in self.related_points]))
        print("--------------------------------------------------------")
