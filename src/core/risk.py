from src.brokers.base import BaseBroker, OrderSide


class RiskManager:

    def __init__(self, max_position_pct: float = 0.10, stop_loss_pct: float = 0.05,
                 daily_loss_limit_pct: float = 0.03, max_open_positions: int = 10):
        self.max_position_pct = max_position_pct
        self.stop_loss_pct = stop_loss_pct
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_open_positions = max_open_positions

    def can_open_position(self, broker: BaseBroker, symbol: str, price: float, quantity: float) -> tuple[bool, str]:
        positions = broker.get_positions()
        balance = broker.get_balance()
        total_value = balance + sum(p.market_value for p in positions.values())

        if len(positions) >= self.max_open_positions:
            return False, f"Max antal positioner ({self.max_open_positions}) uppnått"

        position_value = price * quantity
        if position_value > total_value * self.max_position_pct:
            max_value = total_value * self.max_position_pct
            return False, f"Position ({position_value:.0f}) överskrider max ({max_value:.0f})"

        if position_value > balance:
            return False, f"Otillräckligt kapital ({balance:.0f} tillgängligt)"

        return True, "OK"

    def calculate_position_size(self, broker: BaseBroker, price: float) -> int:
        balance = broker.get_balance()
        positions = broker.get_positions()
        total_value = balance + sum(p.market_value for p in positions.values())
        max_value = total_value * self.max_position_pct
        quantity = int(max_value / price)
        return max(0, quantity)

    def check_stop_loss(self, broker: BaseBroker) -> list[str]:
        symbols_to_sell = []
        for symbol, position in broker.get_positions().items():
            if position.unrealized_pnl_pct <= -self.stop_loss_pct:
                symbols_to_sell.append(symbol)
        return symbols_to_sell
