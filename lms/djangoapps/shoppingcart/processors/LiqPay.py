# -*- coding: utf-8 -*-

__author__ = 'olga'

"""
Implementation of the LiqPay credit card processor
    CC_PROCESSOR_NAME = "LiqPay"
    CC_PROCESSOR = {
        "LiqPay": {
            "public_key": "<public_key>",
            "PURCHASE_ENDPOINT": "<purchase endpoint>"
        }
    }
"""
import hmac
import binascii
import re
import json
import uuid
import logging
from textwrap import dedent
from datetime import datetime
from collections import OrderedDict, defaultdict
from decimal import Decimal, InvalidOperation
from hashlib import sha1
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from edxmako.shortcuts import render_to_string
from shoppingcart.models import Order
from shoppingcart.processors.exceptions import *
from shoppingcart.processors.helpers import get_processor_config
from microsite_configuration import microsite
import base64
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from courseware.courses import get_course_by_id

log = logging.getLogger(__name__)


def render_purchase_form_html(cart, callback_url=None, extra_data=None):
    """
    Renders the HTML of the hidden POST form that must be used to initiate a purchase with LiqPay
    Args:
        cart (Order): The order model representing items in the user's cart.
    Keyword Args:
        callback_url (unicode): The URL that LiqPay should POST to when the user
            completes a purchase.  If not provided, then LiqPay will use
            the URL provided by the administrator of the account
            (LiqPay config, not LMS config).
        extra_data (list): Additional data to include as merchant-defined data fields.
    Returns:
        unicode: The rendered HTML form.
    """
    return render_to_string('shoppingcart/liqpay_form.html', {
        'action': get_purchase_endpoint(),
        'params': get_signed_purchase_params(
            cart, callback_url=callback_url, extra_data=extra_data
        ),
    })


def data_hash(params):
    string = json.dumps(params)
    return base64.b64encode(string)


def data_unhash(string):
    string = base64.b64decode(string)
    return json.loads(string)


def get_purchase_endpoint():
    """
    Return the URL of the payment end-point for LiqPay.
    Returns:
        unicode
    """
    return get_processor_config().get('PURCHASE_ENDPOINT', '')


def get_signed_purchase_params(cart, callback_url=None, extra_data=None):
    """
    This method will return a digitally signed set of CyberSource parameters
    Args:
        cart (Order): The order model representing items in the user's cart.
    Keyword Args:
        callback_url (unicode): The URL that CyberSource should POST to when the user
            completes a purchase.  If not provided, then CyberSource will use
            the URL provided by the administrator of the account
            (CyberSource config, not LMS config).
        extra_data (list): Additional data to include as merchant-defined data fields.
    Returns:
        dict
    """
    return sign(get_purchase_params(cart, callback_url=callback_url, extra_data=extra_data))


def sign(params):
    """
    Sign the parameters dictionary so LiqPay can validate our identity.
    The params dict should contain a key 'signed_field_names' that is a comma-separated
    list of keys in the dictionary.  The order of this list is important!
    Args:
        params (dict): Dictionary of parameters; must include a 'signed_field_names' key
    Returns:
        dict: The same parameters dict, with a 'signature' key calculated from the other values.
    """
    json_object = OrderedDict()

    json_object['signature'] = processor_hash(data_hash(params))
    json_object['data'] = data_hash(params)
    return json_object


def processor_hash(value):
    """
    Calculate the base64-encoded, SHA-1 hash used by LiqPay.

    Args:
        value (string): The value to encode.

    Returns:
        string

    """
    secret_key = get_processor_config().get('SECRET_KEY', '')
    return base64.b64encode(sha1(secret_key + value + secret_key).digest())


def get_purchase_params(cart, callback_url=None, extra_data=None):
    """
    This method will build out a dictionary of parameters needed by CyberSource to complete the transaction
    Args:
        cart (Order): The order model representing items in the user's cart.
    Keyword Args:
        callback_url (unicode): The URL that CyberSource should POST to when the user
            completes a purchase.  If not provided, then CyberSource will use
            the URL provided by the administrator of the account
            (CyberSource config, not LMS config).
        extra_data (list): Additional data to include as merchant-defined data fields.
    Returns:
        dict
    """
    site_name = microsite.get_value('SITE_NAME', settings.SITE_NAME)
    total_cost = cart.total_cost
    amount = "{0:0.2f}".format(total_cost)
    params = OrderedDict()

    params['version'] = 3
    course = get_course_by_id(SlashSeparatedCourseKey.from_deprecated_string(extra_data[0]))
    course_name = course.display_name_with_default

    '{base_url}{dashboard}'.format(
        base_url=site_name,
        dashboard=reverse('dashboard'))
    params['description'] = u'Запис на курс "{course_name}" ({course_num}) | Номер заказу [{course_id}]'.format(
        course_name=course_name,
        course_num=extra_data[0],
        course_id=cart.id
    )

    params['amount'] = amount
    params['currency'] = "uah"
    params['orderNumber'] = "OrderId: {0:d}".format(cart.id)

    params['signed_date_time'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    params['course_id'] = extra_data[0]

    params['course_name'] = course_name

    params['public_key'] = get_processor_config().get('PUBLIC_KEY', '')
    params['type'] = 'buy'

    params['language'] = 'ru'
    # params['signed_date_time'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    if callback_url is not None:
        params['server_url'] = callback_url

    params['server_url'] = get_processor_config().get('SERVER_URL', 'https://59065b71.ngrok.com/shoppingcart/postpay_callback/')
    params['result_url'] = '{base_url}{dashboard}'.format(
        base_url=site_name,
        dashboard=reverse('dashboard'))
    if get_processor_config().get('SANDBOX') or course_name == "sandbox":
        params['sandbox'] = 1

    if callback_url is not None:
        params['override_custom_receipt_page'] = callback_url
        params['override_custom_cancel_page'] = callback_url

    if extra_data is not None:
        # LiqPay allows us to send additional data in "merchant defined data" fields
        for num, item in enumerate(extra_data, start=1):
            key = u"merchant_defined_data{num}".format(num=num)
            params[key] = item

    return params


def process_postpay_callback(params):
    """
    Handle a response from the payment processor.
    Concrete implementations should:
        1) Verify the parameters and determine if the payment was successful.
        2) If successful, mark the order as purchased and call `purchased_callbacks` of the cart items.
        3) If unsuccessful, try to figure out why and generate a helpful error message.
        4) Return a dictionary of the form:
            {'success': bool, 'order': Order, 'error_html': str}
    Args:
        params (dict): Dictionary of parameters received from the payment processor.
    Keyword Args:
        Can be used to provide additional information to concrete implementations.
    Returns:
        dict
    """
    try:
        valid_params = verify_signatures(params)
        order_id_group = re.search('(?<=\[)\d+', valid_params['description'])
        course_name_group = re.search(r'\"(.+?)\"', valid_params['description'])
        order_id = order_id_group.group(0)
        course_name = course_name_group.group(0)

        result = _payment_accepted(
            order_id,
            valid_params['amount'],
            valid_params['currency'],
            valid_params['status']
        )
        if result['accepted']:
            _record_purchase(params, result['order'], course_name)
            return {
                'success': True,
                'order': result['order'],
                'error_html': ''
            }
        else:
            _record_payment_info(params, result['order'])
            return {
                'success': False,
                'order': result['order'],
                'error_html': _get_processor_decline_html(params)
            }
    except CCProcessorException as error:
        log.exception('error processing LiqPay postpay callback')
        # if we have the order and the id, log it
        if hasattr(error, 'order'):
            _record_payment_info(params, error.order)
        else:
            log.info(json.dumps(data_unhash(params.get('data'))))
        return {
            'success': False,
            'order': None,  # due to exception we may not have the order
            'error_html': _get_processor_exception_html(error)
        }


def _record_payment_info(params, order):
    """
    Record the purchase and run purchased_callbacks
    Args:
        params (dict): The parameters we received from LiqPay.
    Returns:
        None
    """
    order.processor_reply_dump = json.dumps(data_unhash(params.get('data')))
    order.save()


def _record_purchase(params, order, course_name):
    """
    Record the purchase and run purchased_callbacks
    Args:
        params (dict): The parameters we received from LiqPay.
        order (Order): The order associated with this payment.
    Returns:
        None
    """
    # Usually, the credit card number will have the form "xxxxxxxx1234"
    # Parse the string to retrieve the digits.
    # If we can't find any digits, use placeholder values instead.
    json_data = data_unhash(params.get('data'))

    ccnum_str = json_data.get('req_card_number', '')
    mm = re.search("\d", ccnum_str)
    if mm:
        ccnum = ccnum_str[mm.start():]
    else:
        ccnum = "####"

    # Mark the order as purchased and store the billing information
    order.purchase(
        first=json_data.get('req_bill_to_forename', ''),
        last=json_data.get('req_bill_to_surname', ''),
        street1=json_data.get('req_bill_to_address_line1', ''),
        street2=json_data.get('req_bill_to_address_line2', ''),
        city=json_data.get('req_bill_to_address_city', ''),
        state=json_data.get('req_bill_to_address_state', ''),
        country=json_data.get('req_bill_to_address_country', ''),
        postalcode=json_data.get('req_bill_to_address_postal_code', ''),
        ccnum=ccnum,
        cardtype=CARDTYPE_MAP[json_data.get('req_card_type', '')],
        course_name=course_name
    )


def _payment_accepted(order_id, auth_amount, currency, decision):
    """
    Check that LiqPay has accepted the payment.
    Args:
        order_num (int): The ID of the order associated with this payment.
        auth_amount (Decimal): The amount the user paid using LiqPay.
        currency (str): The currency code of the payment.
        decision (str): "ACCEPT" if the payment was accepted.
    Returns:
        dictionary of the form:
        {
            'accepted': bool,
            'amnt_charged': int,
            'currency': string,
            'order': Order
        }
    Raises:
        CCProcessorDataException: The order does not exist.
        CCProcessorWrongAmountException: The user did not pay the correct amount.
    """
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        raise CCProcessorDataException(_("The payment processor accepted an order whose number is not in our system."))

    if decision == 'success' or decision == 'sandbox':
        return {
            'accepted': True,
            'amt_charged': auth_amount,
            'currency': currency,
            'order': order
        }
    else:
        return {
            'accepted': False,
            'amt_charged': 0,
            'currency': 'usd',
            'order': order
        }


def _get_processor_decline_html(params):
    """
    Return HTML indicating that the user's payment was declined.

    Args:
        params (dict): Parameters we received from CyberSource.

    Returns:
        unicode: The rendered HTML.

    """
    payment_support_email = microsite.get_value('payment_support_email', settings.PAYMENT_SUPPORT_EMAIL)
    return _format_error_html(
        _(
            "Sorry! Our payment processor did not accept your payment.  "
            "The decision they returned was {decision}, "
            "and the reason was {reason}.  "
            "You were not charged. Please try a different form of payment.  "
            "Contact us with payment-related questions at {email}."
        ).format(
            decision='<span class="decision">{decision}</span>'.format(decision=params['decision']),
            reason='<span class="reason">{reason_code}:{reason_msg}</span>'.format(
                reason_code=params['reason_code'],
                reason_msg='error occurred'
            ),
            email=payment_support_email
        )
    )


def verify_signatures(params):
    """
    Use the signature we receive in the POST back from LiqPay to verify
    the identity of the sender (LiqPay) and that the contents of the message
    have not been tampered with.
    Args:
        params (dictionary): The POST parameters we received from LiqPay.
    Returns:
        dict: Contains the parameters we will use elsewhere, converted to the
            appropriate types
    Raises:
        CCProcessorSignatureException: The calculated signature does not match
            the signature we received.
        CCProcessorDataException: The parameters we received from CyberSource were not valid
            (missing keys, wrong types)
    """
    data = params.get('data')
    json_data = data_unhash(data)
    # First see if the user cancelled the transaction
    # if so, then not all parameters will be passed back so we can't yet verify signatures
    if json_data.get('status') == u'failure':
        raise CCProcessorUserCancelled()

    # Validate the signature to ensure that the message is from CyberSource
    # and has not been tampered with.
    signature = params.get('signature')
    if signature != processor_hash(data):
        raise CCProcessorSignatureException()

    # Validate that we have the paramters we expect and can convert them
    # to the appropriate types.
    # Usually validating the signature is sufficient to validate that these
    # fields exist, but since we're relying on CyberSource to tell us
    # which fields they included in the signature, we need to be careful.
    valid_params = {}
    required_params = [
        ('description', unicode),
        ('currency', str),
        ('status', str),
        ('amount', Decimal),
    ]
    for key, key_type in required_params:
        if key not in json_data:
            raise CCProcessorDataException(
                _(
                    u"The payment processor did not return a required parameter: {parameter}"
                ).format(parameter=key)
            )
        try:
            valid_params[key] = key_type(json_data[key])
        except (ValueError, TypeError, InvalidOperation):
            raise CCProcessorDataException(
                _(
                    u"The payment processor returned a badly-typed value {value} for parameter {parameter}."
                ).format(value=json_data[key], parameter=key)
            )

    return valid_params


def _get_processor_exception_html(exception):
    """
    Return HTML indicating that an error occurred.

    Args:
        exception (CCProcessorException): The exception that occurred.

    Returns:
        unicode: The rendered HTML.

    """
    payment_support_email = microsite.get_value('payment_support_email', settings.PAYMENT_SUPPORT_EMAIL)
    if isinstance(exception, CCProcessorDataException):
        return _format_error_html(
            _(
                u"Sorry! Our payment processor sent us back a payment confirmation that had inconsistent data! "
                u"We apologize that we cannot verify whether the charge went through and take further action on your order. "
                u"The specific error message is: {msg} "
                u"Your credit card may possibly have been charged.  Contact us with payment-specific questions at {email}."
            ).format(
                msg=u'<span class="exception_msg">{msg}</span>'.format(msg=exception.message),
                email=payment_support_email
            )
        )
    elif isinstance(exception, CCProcessorWrongAmountException):
        return _format_error_html(
            _(
                u"Sorry! Due to an error your purchase was charged for a different amount than the order total! "
                u"The specific error message is: {msg}. "
                u"Your credit card has probably been charged. Contact us with payment-specific questions at {email}."
            ).format(
                msg=u'<span class="exception_msg">{msg}</span>'.format(msg=exception.message),
                email=payment_support_email
            )
        )
    elif isinstance(exception, CCProcessorSignatureException):
        return _format_error_html(
            _(
                u"Sorry! Our payment processor sent us back a corrupted message regarding your charge, so we are "
                u"unable to validate that the message actually came from the payment processor. "
                u"The specific error message is: {msg}. "
                u"We apologize that we cannot verify whether the charge went through and take further action on your order. "
                u"Your credit card may possibly have been charged. Contact us with payment-specific questions at {email}."
            ).format(
                msg=u'<span class="exception_msg">{msg}</span>'.format(msg=exception.message),
                email=payment_support_email
            )
        )
    elif isinstance(exception, CCProcessorUserCancelled):
        return _format_error_html(
            _(
                u"Sorry! Our payment processor sent us back a message saying that you have cancelled this transaction. "
                u"The items in your shopping cart will exist for future purchase. "
                u"If you feel that this is in error, please contact us with payment-specific questions at {email}."
            ).format(
                email=payment_support_email
            )
        )
    elif isinstance(exception, CCProcessorUserDeclined):
        return _format_error_html(
            _(
                u"We're sorry, but this payment was declined. The items in your shopping cart have been saved. "
                u"If you have any questions about this transaction, please contact us at {email}."
            ).format(
                email=payment_support_email
            )
        )
    else:
        return _format_error_html(
            _(
                u"Sorry! Your payment could not be processed because an unexpected exception occurred. "
                u"Please contact us at {email} for assistance."
            ).format(email=payment_support_email)
        )


def _format_error_html(msg):
    """ Format an HTML error message """
    return u'<p class="error_msg">{msg}</p>'.format(msg=msg)

CARDTYPE_MAP = defaultdict(lambda: "UNKNOWN")
CARDTYPE_MAP.update(
    {
        '001': 'Visa',
        '002': 'MasterCard',
        '003': 'American Express',
        '004': 'Discover',
        '005': 'Diners Club',
        '006': 'Carte Blanche',
        '007': 'JCB',
        '014': 'EnRoute',
        '021': 'JAL',
        '024': 'Maestro',
        '031': 'Delta',
        '033': 'Visa Electron',
        '034': 'Dankort',
        '035': 'Laser',
        '036': 'Carte Bleue',
        '037': 'Carta Si',
        '042': 'Maestro Int.',
        '043': 'GE Money UK card'
    }
)


