def get_suburbs(): 
    suburbs = {        
        'Sydney City Hotels': {
            'price': 30,
            'image_url': '/static/basecamp/photos/sydney-city-hotels.webp',
            'description': 'Easygo Airport Shuttle provide a shared ride for $25 per person and a private ride for $70 tow persons',
            'extra': ''
        },        
        'Chatswood': {
            'price': 75,
            'image_url': '/static/basecamp/photos/chatswood.webp',
            'description': 'Easygo Airport Shuttle provide a private/shared ride for two persons: $85, for three persons: $95',
            'extra': '*additional $10 per person*'
        },                
        'St Ives': {
            'price': 90,
            'image_url': '/static/basecamp/photos/st-ives.webp',
            'description': 'EasyGo Airport Shuttle provide a private/shared ride for two persons: $100, for three persons: $110',
            'extra': '*additional $10 per person*'
        },
        'Ryde': {
            'price': 75,
            'image_url': '/static/basecamp/photos/ryde.webp',
            'description': 'EasyGo Airport Shuttle provide a private/shared ride for two persons: $85, for three persons: $95',
            'extra': '*additional $10 per person*'
        }, 
        'Hornsby': {
            'price': 110,
            'image_url': '/static/basecamp/photos/hornsby.webp',
            'description': 'EasyGo Airport Shuttle provide a private/shared ride for two persons: $120, for three persons: $130',
            'extra': '*additional $10 per person*'
        },
        'Blacktown': {
            'price': 120,
            'image_url': '/static/basecamp/photos/blacktown.webp',
            'description': 'EasyGo Airport Shuttle provide a private/shared ride for two persons: $130, for three persons: $140',
            'extra': '*additional $10 per person*'
        },    
    }
    return suburbs

suburbs = get_suburbs() 
