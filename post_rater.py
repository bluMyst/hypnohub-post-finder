BASE_RATING = 80

TAG_RATINGS = {
    'death':                    -230,
    'alvin_and_the_chipmunks':  -230,
    'nightmare_fuel':           -230,
    'ed_edd_n_eddy':            -200,
    'dolores_umbridge':         -220,
    'scat':                     -200,
    'weight_gain':              -200,

    'fart':                   -180,
    'the_simpsons':           -180,
    'jiminy_cricket':         -170,
    'fisting':                -160,
    'lilo_and_stich':         -160,
    'human_pet':              -150,
    'robotization':           -150,
    'daria_(series)':         -150,
    'ghost_clown':            -150,
    'animal_transformation':  -140,
    'american_dad':           -140,
    'johnny_test_(series)':   -140,
    'family_guy':             -140,
    'fisting':                -120,
    'huge_nipples':           -120,
    'huge_lips':              -130,
    'breast_expansion':       -115,
    'large_lips':             -115,
    'bimbofication':          -110,
    'fat':                    -110,
    'petrification':          -110,
    'futurama':               -110,

    'huge_cock':              -90,
    'kaa':                    -80,
    'furry':                  -60,
    'transformation':         -60,
    '3d':                     -60,
    'my_little_pony':         -60,
    'corruption':             -60,
    'standing_at_attention':  -60,
    'dollification':          -50,
    'manip':                  -40,
    'snake':                  -40,
    'zombie_walk':            -40,
    'robot':                  -40,
    'pregnant':               -40,
    'feet':                   -20,

    'unaware':         20,
    'orgasm':          30,
    'femdom':          40,
    'orgasm_command':  60,
    'malesub':         60,
    'orgasm_denial':   80,

    'urination':    100,
    'humiliation':  100,
}

TAG_RATINGS = {k.lower(): v for k, v in TAG_RATINGS.items()}

def rate_post(post):
    rating = BASE_RATING + int(post.score)

    for tag in post.tags:
        if tag.lower() in TAG_RATINGS:
            rating += TAG_RATINGS[tag]

def post_filter(post):
    return rate_hypnohub_post(post) > 0
