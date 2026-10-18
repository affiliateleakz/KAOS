import unittest
from coinbase_position_policy import exit_decision

class PositionPolicyTests(unittest.TestCase):
    def decision(self, **kwargs):
        data = dict(base_size='1', entry_notional='100', entry_fees='0.5',
                    mark_price='100', stop_loss_pct='2', take_profit_pct='3',
                    estimated_exit_fee_pct='0.5')
        data.update(kwargs)
        return exit_decision(**data)

    def test_hold_when_fees_mean_no_target(self):
        x = self.decision(mark_price='101')
        self.assertEqual(x['action'], 'HOLD')
        self.assertEqual(x['estimated_net_pnl_usd'], '-0.005')
    def test_stop_loss(self):
        self.assertEqual(self.decision(mark_price='97')['reason'], 'STOP_LOSS')
    def test_take_profit(self):
        self.assertEqual(self.decision(mark_price='105')['reason'], 'TAKE_PROFIT')
    def test_strategy_sell(self):
        self.assertEqual(self.decision(signal='SELL')['reason'], 'KAOS_STRATEGY_SELL')
    def test_invalid_negative_price(self):
        with self.assertRaises(ValueError): self.decision(mark_price='-1')
    def test_invalid_nan(self):
        with self.assertRaises(ValueError): self.decision(mark_price='NaN')
    def test_not_a_live_order(self):
        self.assertFalse(self.decision(signal='SELL')['execution_enabled'])

if __name__ == '__main__': unittest.main()
