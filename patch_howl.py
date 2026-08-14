import re

with open('src/changeops.howl', 'r') as f:
    code = f.read()

# Add lets
let_chain_end_pattern = r'(\s*)\(do\n(\s*)\(for arg \(cli_args\)'
new_lets = '''\g<1>(let (ev_remote_head "")
\g<1>  (let (ev_current_remote_head "")
\g<1>    (let (ev_local_remote_match "false")
\g<1>      (let (ev_ci_status "")
\g<1>        (do
\g<2>    (for arg (cli_args)'''
code = re.sub(let_chain_end_pattern, new_lets, code, count=1)

# Add if matches inside the for loop
if_ci_pattern = r'(\s*)\(if \(= key "risk_ci"\) \(set risk_ci val\)\)'
new_ifs = '''\g<0>
\g<1>(if (= key "remote_head") (set ev_remote_head val))
\g<1>(if (= key "current_remote_head") (set ev_current_remote_head val))
\g<1>(if (= key "local_remote_match") (set ev_local_remote_match val))
\g<1>(if (= key "ci_status") (set ev_ci_status val))'''
code = re.sub(if_ci_pattern, new_ifs, code, count=1)

# Add closing parens
parens_pattern = r'(\s*)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)\)'
code = re.sub(parens_pattern, r'\g<1>))))))))))))))))))))))))))))))))))', code)

with open('src/changeops.howl', 'w') as f:
    f.write(code)
