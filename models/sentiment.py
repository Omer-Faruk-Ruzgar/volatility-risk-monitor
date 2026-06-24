"""Haber basliklarindan VADER tabanli jeopolitik gerilim skoru uretir."""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def score_region(headlines: list) -> float:
    """
    Bir bolgeye ait haber basliklarini analiz eder, 0-10 arasi
    gerilim skoru dondurur. 0 = notr/sakin, 10 = ekstrem negatif.

    VADER compound skoru -1 ile +1 arasinda doner; negatif skorlar
    gerilimi temsil eder, bu yuzden ters ceviriyoruz.
    """
    if not headlines:
        return 0.0

    compound_scores = [_analyzer.polarity_scores(h)["compound"] for h in headlines]
    avg_compound = sum(compound_scores) / len(compound_scores)

    # avg_compound: -1 (cok negatif) .. +1 (cok pozitif)
    # Sadece negatif taraf gerilim olarak yorumlanir
    tension = max(0.0, -avg_compound) * 10
    return round(tension, 1)
