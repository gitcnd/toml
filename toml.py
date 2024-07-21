# toml.py

__version__ = '1.0.20240707'  # Major.Minor.Patch

# Created by Chris Drake.
# read and write .toml files for MicroPython and CircuitPython.  see also: https://github.com/gitcnd/mpy_self
# 
#  import toml
#
#  toml.setenv("key","value") # put None for value to delete the key. # accepts default= file=
#
#  toml.getenv("key") # defaults to /settings.toml
#  toml.getenv("key",file="/my_file.toml",default="value to use if key not found")
#
#  toml.subst_env("Put a $key in a string") # accepts default= file== and ${key} syntax

import os

class toml:
    def __init__(self,cio=None):
        self.settings_file = "./settings.toml"


    def _extr(self,value_str):
        value_str = value_str.strip()
    
        # Handle different quote types
        if value_str.startswith("'") or value_str.startswith('"'):
            q = value_str[0]
            if value_str.startswith(f"{q}{q}{q}"):
                q = value_str[:3]
            
            end_idx = value_str.find(q, len(q))
            while end_idx != -1 and value_str[end_idx-1] == '\\':  # Check for escaped quote
                end_idx = value_str.find(q, end_idx + len(q))
            
            if end_idx == -1:
                raise ValueError("Unterminated string")
    
            return value_str[len(q):end_idx] # value_str[:end_idx + len(q)].strip()
        
        # Handle numeric and other literals
        else:
            return value_str.split('#', 1)[0].strip()


    def mv(self, cmdenv):
        cmd = cmdenv['args'][0]
        if 1:
            target = cmdenv['args'][-1]
            try:
                fstat = os.stat(target)
            except OSError:
                fstat = [0xFCD]
            if fstat[0] & 0x4000:
                if target.endswith("/"):
                    target = target[:-1]
                for path in cmdenv['args'][1:-1]:
                    dest = target + '/' + path
                    if cmd == 'cp':
                        _cp(path, dest)
                    else:
                        os.rename(path, dest)
            else:
                if len(cmdenv['args']) == 3:
                    path = cmdenv['args'][1]
                    try:
                        if cmd == 'cp':
                            _cp(path, target)
                        else:  # mv
                            if not fstat[0] == 0xFCD:
                                os.remove(target)
                            os.rename(path, target)
                    except OSError as e:
                        print(f"{cmd}: {e}")
                else:
                    print("{}: target '{}' is not a directory".format(cmd, target))  # {}: target '{}' is not a directory
    

    def _strip_cmt(self, line):
        quote_char = None
        for i, char in enumerate(line):
            if char in ('"', "'"):
                if quote_char is None:
                    quote_char = char
                elif quote_char == char and (i == 0 or line[i-1] != '\\'):
                    quote_char = None
            elif char == '#' and quote_char is None:
                return line[:i].strip()
        return line.strip()


    def _rw_toml(self, op, file, key, value=None, default=None):
        tmp = file.rsplit('.', 1)[0] + "_new." + file.rsplit('.', 1)[1] # /settings_new.toml
        old = file.rsplit('.', 1)[0] + "_old." + file.rsplit('.', 1)[1] # /settings_old.toml

        try:
            infile = open(file, 'r')
        except OSError:
            if op == 'w':
                open(file, 'w').close() # create empty one if missing
                infile = open(file, 'r')
            else:
                return None

        outfile = open(tmp, 'w') if op == "w" else None
    
        in_multiline = False
        extra_iteration = 0
        line = ''

        while True:
            if extra_iteration < 1:
                iline = infile.readline()
                if not iline:
                    extra_iteration = 1
                    iline = ''  # Trigger the final block execution
            elif extra_iteration == 2:
                extra_iteration = 0
            else:
                break

            line += iline
            iline = ''
            stripped_line = self._strip_cmt(line) # aggressively remove comments too


            if in_multiline:
                if stripped_line.endswith( in_multiline ) and not stripped_line.endswith(f'\\{in_multiline}'):
                    in_multiline = '' # tell it not to re-check next
                else:
                    continue


            if not stripped_line.startswith('#'):
                kv = stripped_line.split('=', 1)
                if not in_multiline == '': # not just ended a multiline
                    if len(kv) > 1 and kv[1].lstrip()[0] in {'"', "'", '(', '{', '['}:
                        s=kv[1].lstrip()[0]
                        in_multiline = { '(': ')', '{': '}', '[': ']' }.get(s, s)
                        if kv[1].lstrip().startswith(f"{s}{s}{s}"):
                            in_multiline = f"{e}{e}{e}"
                        
                        extra_iteration = 2 # skip reading another line, and go back to process this one (which might have the """ or ''' ending already on it) 
                        continue

            #if not stripped_line.startswith('#'):
            #    kv = stripped_line.split('=', 1)
            #    if not in_multiline == '': # not just ended a multiline
            #        if len(kv) > 1 and ( kv[1].strip().startswith('"""') or kv[1].strip().startswith("'''")):
            #            in_multiline = '"""' if kv[1].strip().startswith('"""') else "'''"
            #            extra_iteration = 2 # skip reading another line, and go back to process this one (which might have the """ or ''' ending already on it) 
            #            continue

                if len(kv) > 1 or extra_iteration == 1:
                    if kv[0].strip() == key or extra_iteration == 1:

                        if op != 'w':
                            ret= self._extr(kv[1]).replace("\\u001b", "\u001b") if len(kv) > 1 else None # convert "\x1b[" to esc[ below
                            if ret is not None and ret[0] in '[{(':
                                import json
                                ret=json.loads(ret)
                            return ret

                        elif value == '':
                            line='' # Delete the variable
                            continue
                        elif key:
                            if isinstance(value,(dict, list, tuple)):
                                import json
                                line = '{} = {}\n'.format(key, json.dumps(value))
                            elif value[0] in '+-.0123456789"\'': # Update the variable
                                line = f'{key} = {value}\n'
                            else:
                                #line = f'{key} = "{value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")}"\n' 
                                line = '{} = "{}"\n'.format(key, value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")) 
                            key=None

            in_multiline = False
            if outfile:
                outfile.write(line)
            line=''


        infile.close()
        if outfile:
            outfile.close()
            # Replace old settings with the new settings
            self.mv({'sw': {}, 'args': ['mv', file, old]})
            self.mv({'sw': {}, 'args': ['mv', tmp, file]})
    

    def subst_env(self, value, dflt=None):
        result = ''
        i = 0
        while i < len(value):
            if value[i] == '\\' and i + 1 < len(value) and value[i + 1] == '$':
                result += '$'
                i += 2
            elif value[i] == '$':
                i += 1
                i, expanded = self.exp_env(i,value)
                result += expanded
            else:
                result += value[i]
                i += 1
        return result


    def exp_env(self,start,value):
        if value[start] == '{':
            end = value.find('}', start)
            var_name = value[start + 1:end]
            if var_name.startswith('!'):
                var_name = self.getenv(var_name[1:], f'${{{var_name}}}')
                var_value = self.getenv(var_name, f'${{{var_name}}}')
            else:
                var_value = self.getenv(var_name, f'${{{var_name}}}')
            return end + 1, var_value
        else:
            end = start
            while end < len(value) and (value[end].isalpha() or value[end].isdigit() or value[end] == '_'):
                end += 1
            var_name = value[start:end]
            var_value = self.getenv(var_name, f'${var_name}')
            return end, var_value

    
    def getenv(self, key, dflt=None, file=None):
        return self._rw_toml('r', file or self.settings_file, key) or dflt


    #def setenv(self, cmdenv):
    def setenv(self, key, value=None, file=None):
        self._rw_toml('w', file or self.settings_file, key, value)


t = toml()

def getenv(*args, **kwargs):
    return t.getenv(*args, **kwargs)

def setenv(*args, **kwargs):
    return t.setenv(*args, **kwargs)

def subst_env(*args, **kwargs):
    return t.subst_env(*args, **kwargs)

# import toml
# toml.getenv('USER')
