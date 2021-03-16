strategy = {
    "signal": [
        {
            "name": "hma",
            "properties":{
                "interval": '1h',
                "length": 55,
                "offset": 2
            }
        },
        {
            "name": "ao",
            "properties":{
                "interval": '15m',
                "fast": 6,
                "slow": 38,
                "offset": 2
            }
        },
        {
            "name": "aroon",
            "properties":{
                "interval": '15m',
                "length": 17,
            }
        },
    ],
    "atr": {
        "name": "atr",
        "properties":{
            "interval": '1h',
            "length": 24
        }
    },
    "no-trade-hours": [18,19,20,21,22,23,0,1,2,3,4,5,6,7,8,9],
    "tp-atr": 0.95,
    "sl-atr": 1,
    "risk": 4
}