from src.market_watcher import get_inflation_rate
from src.merit_engine import apply_streak_penalty
from src.database_manager import update_merit_score

def evaluate_price_fairness(vendor_name, last_price, new_price):
    """Flags unfair price hikes compared to market inflation."""
    inflation = get_inflation_rate() # From RapidAPI
    price_increase_pct = ((new_price - last_price) / last_price) * 100
    
    # Logic: If price hike is 2x the inflation rate, it's a penalty
    if price_increase_pct > (inflation * 2):
        penalty = -5
        reason = f"Unfair price hike: {price_increase_pct:.1f}% vs {inflation}% inflation"
        update_merit_score(vendor_name, penalty, reason)
        return False, reason
    
    return True, "Price hike within acceptable market bounds."