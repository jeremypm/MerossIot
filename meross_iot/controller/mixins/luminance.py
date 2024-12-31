import logging
from typing import Optional, Union
from meross_iot.controller.mixins.utilities import DynamicFilteringMixin
from meross_iot.controller.mixins.toggle import ToggleMixin, ToggleXMixin
from meross_iot.model.enums import Namespace, LightMode
from meross_iot.model.plugin.light import LightInfo
from meross_iot.controller.device import ChannelInfo

_LOGGER = logging.getLogger(__name__)


class LuminanceMixin(DynamicFilteringMixin):
    """
    Mixin class that enables luminance control for lights.
    """
    _execute_command: callable
    check_full_update_done: callable

    # async_handle_update: Callable[[Namespace, dict], Awaitable]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # Dictionary keeping the status for every channel
        self._channel_luminance_status = {}
    
    @staticmethod
    def filter(device_ability, device_name,**kwargs):
        return device_ability == Namespace.CONTROL_LUMINANCE.value
    
    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.CONTROL_LUMINANCE:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace {namespace}. Data: {data}")
            payload = data.get('control')
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'control' attribute in push notification data: "
                              f"{data}")
                locally_handled = False
            else:
                # Convert the weird array we get into a sane list
                self._channel_luminance_status.update({item['channel']:item['value'] for item in payload}) 
                # Update the status of every channel that has been reported in this push
                # notification.
                #c = payload['channel']
                #self._update_channel_status(channel=c,
                #                            rgb=payload.get('rgb'),
                #                            luminance=payload.get('luminance'))
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {__name__} mixin data update. Data: {data}")
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            payload = data.get('control')
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'luminance' attribute in push notification data: "
                              f"{data}")
                locally_handled = False
            else:
                # Convert the weird array we get into a sane list
                self._channel_luminance_status.update({item['channel']:item['value'] for item in payload}) 
                locally_handled = True
        
        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    def _set_luminance_value(self,channel,value):
        return {'channel': channel,'value':value}

    async def async_bulk_set_luminance(self,
                                    channelList: dict,
                                    timeout: Optional[float] = None,
                                    ):
        payload = []
        
        for channel,value in channelList.items():
            # Note: we append the payload here.
            payload.append(self._set_luminance_value(channel,value))

        # Only proceed sending the command if any attribute of the light payload was previously computed
        if payload != {}:
            await self._execute_command(method='SET',
                                        namespace=Namespace.CONTROL_LUMINANCE,
                                        payload={"control":payload},
                                        timeout=timeout)
            # Update local state
            self._channel_luminance_status.update(channelList)
    
    async def async_set_luminance(self,
                                  channel: int = 0,
                                  luminance: Optional[int] = None):
        if luminance is not None:
            await self.async_bulk_set_luminance({channel:luminance})

    def get_luminance(self, channel=0, *args, **kwargs) -> Optional[int]:
        """
        Returns the current brightness intensity of the bulb

        :param channel: channel to control, defaults to 0 (bulbs generally have only one channel)

        :return: an integer value from 0 to 100
        """
        self.check_full_update_done()
        luminance = self._channel_luminance_status.get(channel)
        if luminance is None:
            return None
        return luminance