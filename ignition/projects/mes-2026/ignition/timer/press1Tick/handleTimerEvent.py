def handleTimerEvent():
	# VIS-001: sample the 16 Press 1 tags into the gateway buffer. Never let an exception kill the timer.
	try:
		press1.tick()
	except:
		import traceback
		system.util.getLogger("press1").error("tick failed: " + traceback.format_exc())
