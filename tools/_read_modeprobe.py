import json, glob, os
p = 'docs/baseline/mode_probe.json'
d = json.load(open(p, encoding='utf-8'))
print('baseline before:', d['baseline_before'])
print()
print(f"{'mode':16} {'value':>5} {'ret':>5} {'accepted':>8}  rpm_samples        temps")
for c in d['candidates']:
    s = c.get('samples') or []
    rpms = [x.get('rpm') for x in s]
    temps = [x.get('temps') for x in s]
    print(f"{c['name']:16} {c['mode_value']:5} {str(c.get('return')):>5} {str(c.get('accepted')):>8}  {str(rpms):18} {temps}")
print()
print('restored:', d['restore_balanced']['ok'], '| after:', d['restore_balanced']['after'])
