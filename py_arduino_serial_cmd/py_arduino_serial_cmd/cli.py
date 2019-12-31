'''
https://gist.github.com/ShenTengTu/5e40217db8f7a218b28f365a13a14c00
'''

__all__ = ['CLI']

import argparse

class CLI(argparse.ArgumentParser):
    """
    Custom Argument Parser
    """
    def __init__(self, main_params: dict, sub_params: dict):
        # record name of the attribute under which sub-command name will be stored
        self._sub_dest_name = sub_params.get('dest')
        if self._sub_dest_name is None:
            sub_params['dest']  =  'sub_command'
            self._sub_dest_name =  sub_params['dest']
        
        # handler mapping
        self._sub_parser_handler_map = {}

        super().__init__(**main_params)

        # Fix TypeError: __init__() got an unexpected keyword argument
        # `parser_class=argparse.ArgumentParser`
        if 'parser_class' not in sub_params:
            sub_params['parser_class'] = argparse.ArgumentParser
        self._sub_parsers_action = self.add_subparsers(**sub_params)

    def sub_command(self, **kwargs):
        """
        Decorator.
        - Add sub parser with the same name as the function.
        - Register the function as the handler of the sub parser
        """
        def deco(fn):
            fn_name = fn.__name__
            self._sub_parser_handler_map[fn_name] = fn
            self._sub_parsers_action.add_parser(fn_name, **kwargs)
            return fn
        return deco
    
    def sub_command_arg(self, *arg_flags, **arg_conf):
        """
        Decorator.
        - Add a argument to the sub parser with the same name as the function.
        """
        def deco(fn):
            parser = self._sub_parsers_action._name_parser_map[fn.__name__]
            parser.add_argument(*arg_flags, **arg_conf)
            return fn
        return deco
    
    def handle_args(self, args=None, namespace=None):
        """
        Parse args then pass to handler
        """
        namespace = self.parse_args(args, namespace)
        sub_parser_name = getattr(namespace, self._sub_dest_name, None)
        if sub_parser_name is not None:
            fn = self._sub_parser_handler_map.get(sub_parser_name)
            if callable(fn):
                fn(namespace)
        return namespace