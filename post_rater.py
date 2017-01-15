BASE_RATING = 0

TAG_RATINGS = {
    'death':                    -430,
    'alvin_and_the_chipmunks':  -430,
    'nightmare_fuel':           -430,
    'ed_edd_n_eddy':            -400,
    'dolores_umbridge':         -420,
    'scat':                     -400,

    'weight_gain':  -300,

    'the_simpsons':                    -180,
    'spongebob_squarepants_(series)':  -180,
    'jiminy_cricket':                  -170,
    'fisting':                         -160,
    'lilo_and_stich':                  -160,
    'robotization':                    -150,
    'daria_(series)':                  -150,
    'ghost_clown':                     -150,
    'animal_transformation':           -140,
    'american_dad':                    -140,
    'johnny_test_(series)':            -140,
    'family_guy':                      -140,
    'fisting':                         -120,
    'huge_nipples':                    -120,
    'fart':                            -120,
    'breast_expansion':                -115,
    'large_lips':                      -115,
    'bimbofication':                   -110,
    'fat':                             -110,
    'petrification':                   -110,
    'futurama':                        -110,
    'phineas_and_ferb':                -100,

    'pee_drinking':                 -70,
    'huge_lips':                    -70,
    'huge_breasts':                 -70,
    'huge_cock':                    -70,
    'huge_balls':                   -70,
    'memetic_control':              -70,
    'zombie_walk':                  -60,
    'kim_possible_(series)':        -60,
    'human_pet':                    -60,
    'pet_play':                     -60,
    'transformation':               -60,
    '3d':                           -60,
    'lactation':                    -60,
    'age_regression':               -60,
    'diaper':                       -60,
    'my_little_pony':               -60,
    'corruption':                   -60,
    'singing':                      -60,
    'standing_at_attention':        -60,
    'slade':                        -60,
    'before_and_after':             -60,
    'bodysuit':                     -50,
    'dollification':                -50,
    'sonic_the_hedgehog_(series)':  -50,
    'mad_scientist':                -50,
    'pokemon':                      -50,
    'tickling':                     -50,
    'translation_request':          -40,
    'manip':                        -40,
    'robot':                        -40,
    'pregnant':                     -40,
    'super_hero':                   -40,
    'vivian':                       -40,
    'x-naut':                       -40,
    'latex':                        -40,
    'dancing':                      -40,
    'hypnotic_tentacle':            -40,
    'furry':                        -40,
    'deathwish_(manipper)':         -40,
    'haigure':                      -40,
    'hypnotized_hypnotist':         -40,
    'hypnotized_dom':               -40,
    'vore':                         -40,

    # Kaa is so low because Kaa is a snake, so
    # Kaa will also always have the snake tag.
    'kaa':    -40,
    'snake':  -40,

    'foot_worship':   -30,
    'spanking':       -30,
    'male_only':      -30,
    'maledom':        -20,
    'feet':           -20,
    'tentacles':      -20,
    'kaa_eyes':       -20,
    'multiple_subs':  -20,
    'anal':           -20,
    'drool':          -10,
    'pendulum':       -10,
    'spiral':         -10,

    'femdom':          20,
    'crotch_rub':      20,
    'unaware':         20,
    'orgasm':          30,
    'trigger':         30,
    'malesub':         30,
    'incest':          40,
    'orgasm_command':  60,
    'orgasm_denial':   80,

    'urination':       100,
    'humiliation':     100,
    'stage_hypnosis':  100,
}

TAG_RATINGS = {k.lower(): v for k, v in TAG_RATINGS.items()}

def score_factor(score):
    # This was really tricky to write. Extremely high scores shouldn't drown out
    # my tags, but extremely low scores should count for something, too.

    if score <= -1:
        # Can this even happen?
        return -10
    elif 0 <= score <= 10:
        return 0
    elif 11 <= score <= 30:
        return score - 10
    elif 31 <= score <= 400:
        return 10 + score/10
    elif 401 <= score:
        return 50

def rate_post(post):
    rating = BASE_RATING
    rating += score_factor(post.score)

    for tag in post.tags:
        if tag.lower() in TAG_RATINGS:
            rating += TAG_RATINGS[tag]

    return rating

def post_filter(post):
    return rate_post(post) > 0
