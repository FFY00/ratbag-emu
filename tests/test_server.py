# SPDX-License-Identifier: MIT

import pytest

from . import TestBase, MouseData


class TestServer(TestBase):
    @pytest.mark.dependency(name='test_add_device')
    def test_add_device(self, client, name='steelseries-rival310'):
        data = {
            'shortname': 'logitech-g-pro-wireless'
        }
        response = client.post('/devices/add', json=data)
        assert response.status_code == 201
        answer = response.json()
        assert 'id' in answer
        assert 'shortname' in answer
        assert 'name' in answer
        assert 'input_nodes' in answer
        client.delete(f"/devices/{answer['id']}")

    @pytest.mark.dependency(name='test_delete_device',
                            depends=['test_add_device'])
    def test_delete_device(self, client):
        id = self.add_device(client)

        response = client.delete(f'/devices/{id}')
        assert response.status_code == 204

    @pytest.mark.dependency(name='test_list_devices',
                            depends=['test_add_device', 'test_delete_device'])
    def test_list_devices(self, client):
        response = client.get('/devices')
        assert response.status_code == 200
        assert response.json() == []

        id = self.add_device(client)

        response = client.get('/devices')
        assert response.status_code == 200
        answer = response.json()
        assert len(answer) == 1
        assert answer[0]['id'] == id

        client.delete(f'/devices/{id}')

    @pytest.mark.dependency(name='test_get_device',
                            depends=['test_add_device', 'test_delete_device'])
    def test_get_device(self, client):
        id = self.add_device(client)

        response = client.get(f'/devices/{id}')
        assert response.status_code == 200
        answer = response.json()
        assert 'id' in answer
        assert 'shortname' in answer
        assert 'name' in answer
        assert 'input_nodes' in answer

        client.delete(f'/devices/{id}')

    @pytest.mark.dependency(name='test_get_dpi',
                            depends=['test_add_device', 'test_delete_device'])
    def test_get_dpi(self, client, dpi_id=0):
        dpi = 800

        id = self.add_device(client,{
            'is_active': True,
            'resolutions': [
                {
                    'is_active': True,
                    'xres': dpi,
                    'dpi_min': 100,
                    'dpi_max': 16000
                }
            ]
        })
        response = client.get(f'/devices/{id}/phys_props/dpi/{dpi_id}')
        assert response.status_code == 200
        assert response.json() == dpi

        client.delete(f'/devices/{id}')

    @pytest.mark.dependency(name='test_set_dpi',
                            depends=['test_add_device', 'test_delete_device', 'test_get_dpi'])
    def test_set_dpi(self, client, dpi_id=0):
        id = self.add_device(client, {
            'is_active': True,
            'resolutions': [
                {
                    'is_active': True,
                    'xres': 800,
                    'dpi_min': 100,
                    'dpi_max': 16000
                }
            ]
        })

        new_dpi = 6666
        response = client.put(f'/devices/{id}/phys_props/dpi/{dpi_id}', json=new_dpi)
        assert response.status_code == 200

        response = client.get(f'/devices/{id}/phys_props/dpi/{dpi_id}')
        assert response.status_code == 200
        assert response.json() == new_dpi

        client.delete(f'/devices/{id}')

    @pytest.mark.dependency(name='test_get_active_dpi',
                            depends=['test_add_device', 'test_delete_device', 'test_get_dpi'])
    def test_get_active_dpi(self, client):
        self.test_get_dpi(client, 'active')

    @pytest.mark.dependency(name='test_set_active_dpi',
                            depends=['test_add_device', 'test_delete_device', 'test_set_dpi', 'test_get_active_dpi'])
    def test_set_active_dpi(self, client):
        self.test_set_dpi(client, 'active')

    @pytest.mark.dependency(name='test_get_led',
                            depends=['test_add_device', 'test_delete_device'])
    def test_get_led(self, client):
        led_id = 0

        color = [
            0xFF,
            0xFF,
            0xFF
        ]

        id = self.add_device(client, {
            'is_active': True,
            'leds': [
                {
                    'color': color
                }
            ]
        })

        response = client.get(f'/devices/{id}/phys_props/leds/{led_id}')
        assert response.status_code == 200
        assert response.json() == color

        client.delete(f'/devices/{id}')

    @pytest.mark.dependency(name='test_set_led',
                            depends=['test_add_device', 'test_delete_device', 'test_get_led'])
    def test_set_led(self, client):
        led_id = 0

        id = self.add_device(client, {
            'is_active': True,
            'leds': [
                {
                    'color': [0xFF, 0xFF, 0xFF]
                }
            ]
        })

        color = [
            0xAA,
            0xBB,
            0xCC
        ]

        response = client.put(f'/devices/{id}/phys_props/leds/{led_id}', json=color)
        assert response.status_code == 200

        response = client.get(f'/devices/{id}/phys_props/leds/{led_id}')
        assert response.status_code == 200
        assert response.json() == color

        client.delete(f'/devices/{id}')

    @pytest.mark.dependency(name='test_device_event',
                            depends=['test_add_device', 'test_delete_device'])
    def test_device_event(self, client):
        id = self.add_device(client, {
            'is_active': True,
            'resolutions': [
                {
                    'is_active': True,
                    'xres': 1000,
                    'rate': 1000
                }
            ]
        })

        # Send event
        x = y = 5
        data = [
            {
                'start': 0,
                'end': 500,
                'action': {
                    'type': 'xy',
                    'x': x,
                    'y': y
                }
            }
        ]
        received = self.simulate(client, id, data)

        dpi = client.get(f'/devices/{id}/phys_props/dpi/active').json()

        expected = MouseData.from_mm(dpi, x=x, y=y)

        assert expected.x - 1 <= received.x <= expected.x + 1
        assert expected.y - 1 <= received.y <= expected.y + 1

        client.delete(f'/devices/{id}')
