check.pop('error',None)
check['start']=time.monotonic()-30
check['handle']=unreal.register_slate_post_tick_callback(tick)
