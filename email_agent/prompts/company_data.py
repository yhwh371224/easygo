# company_data.py
# EasyGo Airport Shuttle - Company Knowledge Base
# Used as context for Claude API email reply generation

COMPANY_INFO = """
COMPANY: EasyGo Airport Shuttle
LOCATION: Sydney, Australia
SERVICE: Professional private airport transfer service to/from Sydney Airport
  (Both International and Domestic Terminals)
WEBSITE: easygoshuttle.com.au
SERVICE AREAS: Sydney CBD, North Shore, Inner West, Western Sydney, and all major Sydney regions

KEY FEATURES:
- 100% private transfers — no shared rides, no unexpected stops
- Real-time flight tracking at no extra cost
- Driver meets passengers at the designated airport meeting point
- Fixed pricing — no surge pricing, no hidden fees
- Airport parking fees included in all fares
- Door-to-door service
- Friendly, professional drivers who assist with luggage
- Bus-lane access (advantage over Uber/DiDi)

VEHICLES:
- 8 to 13 seater maxi vans
- Spacious with generous luggage capacity
- Suitable for families, large groups, and oversized luggage

ADDITIONAL SERVICES:
- Cruise ship connections
- Concerts, weddings, night events, sporting events
- Group touring
"""

BOOKING_POLICY = """
BOOKING POLICY:
- Bookings must be made at least 24 hours before the flight
- Accepted via: email, SMS, or formal booking form (website)
- If booking within 24 hours of flight, contact us as soon as possible
- All bookings are subject to availability at time of reservation

PAYMENT:
- Accepted: American Express, MasterCard, Visa — paid online in advance
- Full payment must be made in advance for ALL bookings
- Cash is NOT accepted; drivers do not take cash or card payments on the day
- Fixed fares — price quoted at booking is what you pay
"""

CANCELLATION_POLICY = """
DEPOSIT & CANCELLATION POLICY:
- A deposit (or full payment, depending on booking type) is required to confirm a booking
- If a deposit was paid, refunds apply to the deposit; if full payment was made, refunds apply to the full amount paid
- All cancellations must be requested in writing (email)
- The refund tier is determined by the time the cancellation email is SENT, not when it is read or acknowledged

Standard bookings (individual/small group bookings):
- More than 24 hours before pickup: 100% refund
- Between 12 and 24 hours before pickup: 50% refund
- Less than 12 hours before pickup, or no-show: no refund
  (a travel credit may be offered at EasyGo's discretion for genuine last-minute changes; excludes no-shows)

Group & Charter bookings (larger group, charter, special luggage, or multi-day bookings, as reasonably determined by EasyGo):
- More than 48 hours before pickup: 50% refund
- Less than 48 hours before pickup: no refund

Force majeure exception:
- The tiers above do NOT apply where cancellation is due to circumstances beyond the client's control,
  including flight cancellations, flight delays, or severe weather
- In these cases a full refund (of deposit or full payment, as applicable) is provided upon submission of
  supporting documentation (e.g. airline cancellation notice, delay confirmation)

Amendments (date/time changes):
- Changes after confirmation are accepted subject to availability
- EasyGo may charge an amendment fee in addition to any other applicable charges
"""

LUGGAGE_POLICY = """
LUGGAGE POLICY:
Standard allowance:
- 1 suitcase + 1 piece of hand luggage per person (included)

Additional luggage surcharges:
- Extra luggage item: $5.00 per item
- Surfboards / Snow Skis (max 2m): $20.00 per item
- Bike in bike box: $20.00 per item
- Golf clubs: $10.00 per set
- Unusual or oversized items: price on application (must advise at booking)
"""

CHILD_SEAT_POLICY = """
CHILD SEAT POLICY:
- Infant seats and baby capsules available
- Child seats: $10 each
"""

WAITING_AND_ARRIVAL_POLICY = """
AIRPORT PICKUP & WAITING POLICY:
- Drivers monitor flight arrivals in real time
- Driver details (name, contact number, vehicle info, meeting point) sent via email on the arrival day
- Passengers should check email after landing and before exiting terminal
- Meeting point info: easygoshuttle.com.au/meeting_point (driver will advise if changed)

If flight is delayed:
- Contact us as soon as possible
- Vehicles may need to depart for next scheduled pickup if delay is significant
- We will make every effort to arrange another driver (subject to availability)
- Without any contact, a refund may not be available

For departures:
- Delays greater than 5 minutes from booking pickup time may incur additional charges
- Additional waiting time: $2 per minute after 5 minutes
- Returning to pickup location while en route: $2 per minute (driver may refuse if schedule is affected)
"""

VEHICLE_CONDUCT = """
VEHICLE CONDUCT POLICY:
- Food and beverages are NOT permitted on any EasyGo vehicle
- Alcohol consumption and smoking are NOT permitted by law
- Passengers are responsible for any damage or soiling of the vehicle
- Driver has discretion to stop and disembark passengers engaging in unacceptable, illegal, or unruly behaviour
- Route taken is at sole discretion of the driver
"""

COMMUNICATIONS = """
COMMUNICATIONS:
- All client communications conducted via email
- It is the passenger's responsibility to regularly check their email
- EasyGo will not be held liable for issues arising from failure to check or respond to emails
- Any redirection, additional pickup/dropoff, or special requests must be communicated in advance and are subject to approval
  — extra charges may apply
"""

FAQ = """
FREQUENTLY ASKED QUESTIONS:

Q: What is included in the price? Are there any hidden charges?
A: The price includes the airport parking fee. There are no hidden charges and no extra waiting fees for flight delays. Our pricing is fixed and competitive.

Q: What if my flight is delayed?
A: No problem — our drivers track your flight in real time. Simply proceed to the meeting point and your driver will be waiting at no extra charge. Check your email and phone for any updates from us.

Q: What payment options are available?
A: We accept all major credit cards (American Express, MasterCard, Visa). Full payment must be made online in advance — our drivers do not accept cash.

Q: Do you offer infant seats or baby capsules?
A: Yes. Child seats are available for $10 each. Please specify the number required at time of booking.

Q: How many passengers can fit in your vehicle?
A: Our maxi vans accommodate up to 13 passengers — ideal for families, large groups, and travellers with lots of luggage.

Q: How many bags can I bring?
A: Each passenger is allowed 1 standard bag plus 1 carry-on item. Additional or oversized luggage (golf clubs, prams, ski equipment) must be advised in advance — surcharges apply.

Q: Is it a shared or private transfer?
A: 100% private. Your booking is exclusively for your group — no shared rides, no unexpected stops, no waiting for other passengers.

Q: Do you service Sydney CBD hotels?
A: Yes. We provide transfers to and from all Sydney CBD hotels, serviced apartments, and city accommodations — directly to your door.

Q: Which areas do you service?
A: Sydney CBD, North Shore, Inner West, and Western Sydney suburbs. Use our online booking system to check availability for your specific suburb.

Q: How will I meet my driver?
A: Keep your phone on and check your email after landing. We'll send driver name, contact number, vehicle info, and meeting point the evening before your service. Drivers monitor your flight in real time.

Q: Where is the meeting point?
A: Follow the guide at easygoshuttle.com.au/meeting_point. Your driver will contact you if there's any change.

Q: What should I do after collecting baggage?
A: Send a quick message to your driver or email us before exiting the terminal to help coordinate your pickup smoothly.

Q: What if my flight or pickup time changes?
A: Contact us anytime by email — we're always happy to assist.

Q: Can I cancel my booking?
A: Yes, by email. For standard bookings: full refund more than 24 hours before pickup, 50% refund between 12 and 24 hours, and no refund within 12 hours or for no-shows. Group & Charter bookings: 50% refund more than 48 hours before pickup, no refund within 48 hours. If your flight is cancelled or delayed, or there is severe weather, you get a full refund once you send supporting documentation (e.g. the airline's cancellation notice). Date or time changes are subject to availability.
"""


# def get_relevant_context(email_content):
#     """
#     이메일 내용에서 키워드를 감지해서
#     관련된 회사 자료 섹션만 골라서 반환
#     """
#     context = []
#     email = email_content.lower()
#
#     if any(w in email for w in ["cancel", "refund", "reschedule", "rebook"]):
#         context.append(CANCELLATION_POLICY)
#
#     if any(w in email for w in ["luggage", "bag", "suitcase", "golf", "ski", "bike", "surfboard"]):
#         context.append(LUGGAGE_POLICY)
#
#     if any(w in email for w in ["child", "baby", "infant", "seat", "capsule", "kid"]):
#         context.append(CHILD_SEAT_POLICY)
#
#     if any(w in email for w in ["pay", "payment", "card", "cash", "price", "charge", "fee", "cost"]):
#         context.append(BOOKING_POLICY)
#
#     if any(w in email for w in ["delay", "flight", "wait", "meet", "driver", "late", "arrive", "arrival", "pickup", "pick up"]):
#         context.append(WAITING_AND_ARRIVAL_POLICY)
#
#     if any(w in email for w in ["book", "booking", "reserve", "reservation", "schedule"]):
#         context.append(BOOKING_POLICY)
#
#     if any(w in email for w in ["smoke", "alcohol", "food", "drink", "damage", "behaviour"]):
#         context.append(VEHICLE_CONDUCT)
#
#     if any(w in email for w in ["email", "contact", "communicate", "message", "redirect", "stop"]):
#         context.append(COMMUNICATIONS)
#
#     # 중복 제거
#     context = list(dict.fromkeys(context))
#
#     # FAQ는 항상 포함
#     context.append(FAQ)
#
#     return "\n\n".join(context)


# Combined full context for Claude API system prompt (필요시 사용)
FULL_COMPANY_CONTEXT = f"""
{COMPANY_INFO}

{BOOKING_POLICY}

{CANCELLATION_POLICY}

{LUGGAGE_POLICY}

{CHILD_SEAT_POLICY}

{WAITING_AND_ARRIVAL_POLICY}

{VEHICLE_CONDUCT}

{COMMUNICATIONS}

{FAQ}
"""
