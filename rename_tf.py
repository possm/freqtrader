with open('user_data/strategies/WolfQuantEdge_2h.py', 'r') as f:
    code = f.read()

code = code.replace('class WolfQuantEdge(KrakenSlippageMixin, IStrategy):', 'class WolfQuantEdge_2h(KrakenSlippageMixin, IStrategy):')
code = code.replace('class WolfQuantEdge(IStrategy, KrakenSlippageMixin):', 'class WolfQuantEdge_2h(IStrategy, KrakenSlippageMixin):')

with open('user_data/strategies/WolfQuantEdge_2h.py', 'w') as f:
    f.write(code)

