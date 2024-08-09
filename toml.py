# toml.py

__version__ = '1.0.20240809'  # Major.Minor.Patch

# Created by Chris Drake.
# read and write .toml files for MicroPython and CircuitPython.  see also: https://github.com/gitcnd/mpy_self
# 
#  The ways to use this
#
#  #1 defaults to using the file /settings.toml 
# 
#  import toml
#
#  toml.setenv("key","value") # put None for value to delete the key. # accepts default= file=
#
#  toml.getenv("key") # defaults to /settings.toml
#  toml.getenv("key",file="/my_file.toml",default="value to use if key not found")
#  toml.getenv("WIFI",subst=True) # replace any $VARIABLES found inside the key (e.g. welcome="Hi from $HOSTNAME >>>" etc)
#
#  toml.subst_env("Put a $key in a string") # accepts default= file== and ${key} syntax
#
#  #2 specify your own .toml file
#
#  import toml
#  t = toml.toml("my_settings_tst.toml")
#  t.getenv("USER")
#  t.getenv("WIFI",subst=True)
#  t.setenv("PASSWORD","mypass")
#  t.subst_env("My password is $PASSWORD !")
#
# Uses  4816 bytes RAM (2.98%)


import os

class toml:
    t=None

    def __init__(self,file=None,cio=None):
        self.settings_file = file if file else "/settings.toml"

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
        if "#" in line: # don't look if there is none
            if any(char in line for char in ['"', "'"]): # don't bother dealing with # inside quotes if there aren't any quotes either
                for i, char in enumerate(line):
                    if char in ('"', "'"):
                        if quote_char is None:
                            quote_char = char
                        elif quote_char == char and (i == 0 or line[i-1] != '\\'):
                            quote_char = None
                    elif char == '#' and quote_char is None:
                        return line[:i].strip()
            else:
                line=line.split('#', 1)[0] # no quotes
        return line.strip()


    def _rw_toml(self, op, file, key, value=None, default=None, subst=False, include=False): # key is [list] (1 elem for set)
        retd={}
        order=list(key)

        try:
            infile = [ open(file, 'r') ]
        except OSError:
            if op == 'w':
                open(file, 'w').close() # create empty one if missing
                return default

        outfile = None
        if op == "w":
            tmp = file.rsplit('.', 1)[0] + "_new." + file.rsplit('.', 1)[1] # /settings_new.toml
            outfile = open(tmp, 'w')
    
        extra_iteration = 0
        line = ''
        sline = ''
        inside_json = False

        while True:
            if extra_iteration < 1:
                iline = infile[-1].readline()
                while not iline and len(infile) >1:
                    infile[-1].close()
                    infile.pop()
                    iline = infile[-1].readline()
                if not iline:
                    if op == 'w':
                        extra_iteration = 1
                        iline = ''  # Trigger the final block execution
                    else:
                        break
            else:
                break

            line += iline
            if include and iline.startswith('#include'):
                ifile=self._strip_cmt(iline[9:])
                if subst:
                    ifile=self.subst_env(ifile, default=None)
                try:
                    infile.append( open(ifile, 'r') )
                except Exception as e:
                    raise Exception(f"#include {ifile}: {e}")

            iline=self._strip_cmt(iline)
            sline += iline # aggressively remove comments too

            kv = sline.split('=', 1)

            if not inside_json and len(kv)>1 and kv[1].strip()[0] in {'{', '['}:          # ('{' in iline or '[' in iline):
                inside_json = True
            if inside_json:
                if sline.count('{') == sline.count('}') and sline.count('[') == sline.count(']'):
                    inside_json = False
            if inside_json:
                continue

            if len(kv) > 1 or extra_iteration == 1: # extra_iteration means "write if not found"
                kvs=kv[0].strip()
                if kvs in key or extra_iteration == 1:

                    if op != 'w':
                        #if not len(kv) > 1: return None # cannot happen if op != 'w'
                        key.remove(kvs)
                        ret= ''.join(chr(int(part[:2], 16)) + part[2:] if i > 0 else part for i, part in enumerate(self._extr(kv[1]).split("\\x"))) # expand escape chars etc
                        if subst:
                            ret=self.subst_env(ret, default=None)
                        if ret[0] in '[{(':
                            import json
                            ret=json.loads(ret)
                        retd[kvs]=ret
                        if not key: # got it/them all
                            break


                    elif value == '':
                        line='' # Delete the variable
                        continue
                    elif key is not None:
                        if isinstance(value,(dict, list, tuple)):
                            import json
                            line = '{} = {}\n'.format(key[0], json.dumps(value))
                        elif value[0] in '+-.0123456789"\'': # Update the variable
                            line = f'{key[0]} = {value}\n'
                        else:
                            line = '{} = "{}"\n'.format(key[0], value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")) 
                        key=None


            if outfile:
                outfile.write(line)
            line=''
            sline=''


        infile[-1].close()
        if op != 'w':
            ret=[]
            for key in order:
                ret.append(retd.get(key, default))
            if len(order)>1:
                return ret
            else:
                return ret[0]
                
        if outfile:
            outfile.close()
            old = file.rsplit('.', 1)[0] + "_old." + file.rsplit('.', 1)[1] # /settings_old.toml
            # Replace old settings with the new settings
            self.mv({'sw': {}, 'args': ['mv', file, old]})
            self.mv({'sw': {}, 'args': ['mv', tmp, file]})


    def subst_env(self, value, default=None):
        result = ''
        i = 0
        while i < len(value):
            if value[i] == '\\' and i + 1 < len(value) and value[i + 1] == '$':
                result += '$'
                i += 2
            elif value[i] == '$':
                i += 1
                i, expanded = self.exp_env(i,value,default)
                result += expanded
            else:
                result += value[i]
                i += 1
        return result


    def exp_env(self, start, value, default=None):
        if value[start] == '{':
            end = value.find('}', start)
            var_name = value[start + 1:end]
            if var_name.startswith('!'):
                var_name = self.getenv(var_name[1:], f'${{{var_name}}}', default)
                var_value = self.getenv(var_name, f'${{{var_name}}}', default)
            else:
                var_value = self.getenv(var_name, f'${{{var_name}}}')
            return end + 1, var_value
        else:
            end = start
            while end < len(value) and (value[end].isalpha() or value[end].isdigit() or value[end] == '_'):
                end += 1
            var_name = value[start:end]
            var_value = self.getenv(var_name, f'${var_name}', default)
            return end, var_value

    
    def getenv(self, key, default=None, file=None, subst=False, include=False):
        if isinstance(key, (list, tuple)):
            return self._rw_toml('r', file or self.settings_file, key, default=default, subst=subst, include=include)
        return self._rw_toml('r', file or self.settings_file, [key], subst=subst, default=default, include=include)


    def setenv(self, key, value=None, file=None, subst=False):
        self._rw_toml('w', file or self.settings_file, [key], value=value, subst=subst)


    @classmethod
    def get(cls, *args, **kwargs):
        if cls.t is None:
            cls.t = toml()
        return cls.t.getenv(*args, **kwargs)

    @classmethod
    def set(cls, *args, **kwargs):
        if cls.t is None:
            cls.t = toml()
        return cls.t.setenv(*args, **kwargs)

    @classmethod
    def subst(cls, *args, **kwargs):
        if cls.t is None:
            cls.t = toml()
        return cls.t.subst_env(*args, **kwargs)

def getenv(*args, **kwargs):
    return toml.get(*args, **kwargs)

def setenv(*args, **kwargs):
    return toml.set(*args, **kwargs)

def subst_env(*args, **kwargs):
    return toml.subst(*args, **kwargs)
