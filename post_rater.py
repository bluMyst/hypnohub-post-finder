import configparser
cfg = configparser.ConfigParser()
cfg.read('config.cfg')

def score_factor(score):
    # This was really tricky to write. Extremely high scores shouldn't drown out
    # my tags, but extremely low scores should count for something, too.

    if score <= -1:
        # Can this even happen?
        print("Woah! Score less than zero:", score)
        return -10
    elif 0 <= score <= 10:
        return 0
    elif 11 <= score <= 30:
        return score - 10
    elif 31 <= score <= 400:
        return 10 + score/10
    elif 401 <= score:
        return 50

def rate_post(post, explain=False):
    """ Rate a post.

    If explain is truthy then return a tuple of (rating, explanation) where
    explanation is a human-readable string showing how we arrived at the rating
    we did.
    """
    rating = cfg['General'].getfloat('Base Rating')
    sf = score_factor(post.score)
    rating += sf

    if explain:
        explanation  = 'base rating: {rating:.0f}\n'.format(**locals())
        explanation += ('score_factor({post.score})'
                        ' -> {sf:.0f}\n').format(**locals())

    for tag in post.tags:
        # CFG values are case insensitive, even when using 'in'.
        if tag in cfg['Tag Ratings']:
            tag_rating = cfg['Tag Ratings'].getfloat(tag)
            rating += tag_rating

            if explain:
                explanation += "{tag}: {tag_rating:.0f}\n".format(**locals())

    if explain:
        explanation += "-"*30 + "\n"
        explanation += "{rating:.0f}\n".format(**locals())
        return rating, explanation
    else:
        return rating

def post_filter(post):
    return rate_post(post) > 0
