import logging
from typing import Optional

from meross_iot.controller.mixins.utilities import DynamicFilteringMixin
from meross_iot.model.enums import Namespace, OnlineStatus

_LOGGER = logging.getLogger(__name__)


class SystemAllMixin(DynamicFilteringMixin):
    _execute_command: callable
    #async_handle_update: Callable[[Namespace, dict], Awaitable]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

    @staticmethod
    def filter(device_ability : str, device_name : str,**kwargs):
        return device_ability == Namespace.SYSTEM_ALL.value
    
    async def _async_request_update(self, timeout: Optional[float] = None, *args, **kwargs) -> None:
        result = await self._execute_command(method="GET",
                                             namespace=Namespace.SYSTEM_ALL,
                                             payload={},
                                             timeout=timeout)

        # Once we have the response, update all the mixin which are interested
        await self.async_handle_all_updates(namespace=Namespace.SYSTEM_ALL, data=result)


class SystemOnlineMixin(DynamicFilteringMixin):
    _online: OnlineStatus
    #async_handle_update: Callable[[Namespace, dict], Awaitable]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

    @staticmethod
    def filter(device_ability : str, device_name : str,**kwargs):
        return device_ability == Namespace.SYSTEM_ONLINE.value
    
    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            online_data = data.get('all').get('system').get('online')
            status = OnlineStatus(int(online_data.get("status")))
            self._online = status
            locally_handled = True

        return locally_handled

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.SYSTEM_ONLINE:
            _LOGGER.debug(f"OnlineMixin handling push notification for namespace {namespace}")
            payload = data.get('online')
            if payload is None:
                _LOGGER.error(f"OnlineMixin could not find 'online' attribute in push notification data: "
                              f"{data}")
                locally_handled = False
            else:
                status = OnlineStatus(int(payload.get("status")))
                self._online = status
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        return locally_handled
