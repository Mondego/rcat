import pstats

p = pstats.Stats('jigsaw.bench')
p.sort_stats('cum').print_stats(.5, 'init').print_stats()
