def classFactory(iface):
    from .segregation_plugin import SegregationPlugin
    return SegregationPlugin(iface)
