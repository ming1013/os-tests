import unittest
from os_tests.libs import utils_lib
from os_tests.libs.resources import UnSupportedAction
import time
import os
import os_tests
import random

class TestStorage(unittest.TestCase):

    def _blktests_run(self, case_name=None):
        '''
        Run specify blktests test case.
        Arguments:
            test_instance {avocado Test instance} -- avocado test instance
        '''
        test_disk = self._get_test_disk()
        cmd = "sudo bash -c \"echo 'TEST_DEVS=({})' > /usr/local/blktests/config\"".format(test_disk)
        utils_lib.run_cmd(self, cmd, expect_ret=0)
        cmd = "cd /usr/local/blktests/; sudo ./check {}".format(case_name)
        utils_lib.run_cmd(self, cmd, expect_ret=0, expect_not_kw="failed", timeout=2400)

    def _get_test_disk(self):
        '''
        Look for non-boot disk to do test
        '''
        test_disk = None
        cmd = "lsblk -r --output NAME,MOUNTPOINT|awk -F' ' '{if($2) printf\"%s \",$1}'"
        output = utils_lib.run_cmd(self, cmd, expect_ret=0)
        mount_disks = output.split(' ')
        cmd = 'lsblk -d --output NAME|grep -v NAME'
        output = utils_lib.run_cmd(self, cmd, expect_ret=0)
        disk_list = output.split('\n')
        for disk in disk_list:
            disk_in_use = False
            if not disk:
                continue
            for mount_disk in mount_disks:
                if disk in mount_disk:
                    self.log.info('Disk is mounted: {}'.format(disk))
                    disk_in_use = True
                    break
            if not disk_in_use:
                #cmd = 'sudo wipefs -a /dev/{}'.format(disk) #comment this line for bz2074486
                cmd = 'sudo mkfs.ext3 /dev/{} -F'.format(disk)
                ret = utils_lib.run_cmd(self, cmd, ret_status=True, msg='test can clean fs on {}'.format(disk))
                if ret == 0:
                    test_disk = disk
                    break
                else:
                    self.log.info('Cannot clean fs on {} - skip'.format(disk))
                    continue
        if test_disk:
            self.log.info('Test disk is found: {}'.format(test_disk))
        else:
             self.skipTest("No free disk for testing.")
        return '/dev/' + test_disk

    def setUp(self):
        utils_lib.init_case(self)
        utils_dir = os.path.realpath(os_tests.__file__)
        utils_dir = os.path.dirname(utils_dir) + '/utils'
        if utils_lib.is_arch(self, arch='aarch64'):
            blktests_rpm = utils_dir + '/blktests-master.aarch64.rpm'
            blktests_rpm_tmp = '/tmp/blktests-master.aarch64.rpm'
        else:
            blktests_rpm = utils_dir + '/blktests-master.x86_64.rpm'
            blktests_rpm_tmp = '/tmp/blktests-master.x86_64.rpm'
        if not utils_lib.is_pkg_installed(self, pkg_name='blktests',is_install=False) and 'blktests' in self.id():
            if self.params['remote_node'] is not None:
                self.log.info('Copy {} to remote'.format(blktests_rpm))
                self.SSH.put_file(local_file=blktests_rpm, rmt_file=blktests_rpm_tmp)
                blktests_rpm = blktests_rpm_tmp
        if 'blktests' in self.id():
            utils_lib.pkg_install(self, pkg_name='blktests', pkg_url=blktests_rpm)
        self.cursor = utils_lib.get_cmd_cursor(self, timeout=120)

    def test_storage_blktests_block(self):
        '''
        case_name:
            test_storage_blktests_block
        case_priority:
            1
        component:
            kernel
        bugzilla_id:
            1464851
        polarion_id:
            RHEL7-98753
        maintainer:
            xiliang@redhat.com
        description:
            Run blktests block.
        key_steps:
            1. Install blktests
            2. # cd /usr/local/blktests/
            3. # ./check block
        expected_result:
            No failure case found

        '''
        self._blktests_run(case_name="block")

    def test_storage_blktests_nvme(self):
        '''
        case_name:
            test_storage_blktests_nvme
        case_priority:
            1
        component:
            kernel
        bugzilla_id:
            1464851
        polarion_id:
            RHEL7-98753
        maintainer:
            xiliang@redhat.com
        description:
            Run blktests nvme.
        key_steps:
            1. Install blktests
            2. # cd /usr/local/blktests/
            3. # ./check nvme
        expected_result:
            No failure case found
        '''
        self._blktests_run(case_name="nvme")

    def test_growpart(self):
        """
        case_tag:
            cloudinit,storage
        case_name:
            test_growpart
        component:
            cloud-utils-growpart
        bugzilla_id:
            2063921
        is_customer_case:
            True
        maintainer:
            xuazhao@redhat.com
        description:
            check if pvs can work after growpart
        key_steps:
            1.make disk parted
            2.pvcreate vgcreate
            3.growpart
            4.check if pvs and vgs still exists after growpart
        expect_result:
            pvs can show normally,e.g:
            PV VG Fmt Attr PSize PFree
        debug_want:
            N/A
        """
        if(not self._get_test_disk()):
            self.skipTest("test disk not found")
        else:
            test_disk = self._get_test_disk()
        utils_lib.is_cmd_exist(self,"growpart")
        utils_lib.is_pkg_installed(self,"lvm2")
        test_part = test_disk + "1"

        cmd = 'sudo wipefs -a {}'.format(test_disk)
        utils_lib.run_cmd(self,cmd,msg="wipe all fs from {}".format(test_disk))
        cmd = " sudo parted -s {} mklabel gpt mkpart primary ext4 1MB 1024MB".format(test_disk)
        utils_lib.run_cmd(self,cmd,msg = "make disk part")

        cmd = "sudo pvcreate {} -ff -y".format(test_part)
        utils_lib.run_cmd(self,cmd,msg= "create lvm on disk")
        time.sleep(2)

        cmd = "sudo vgcreate datavga {}".format(test_part)
        utils_lib.run_cmd(self,cmd,msg="create vg group")
        time.sleep(2)

        cmd = "sudo growpart {} 1".format(test_disk)
        utils_lib.run_cmd(self,cmd,msg="run growpart")
        time.sleep(2)

        utils_lib.run_cmd(self,"sudo pvs",expect_kw="datavga",msg="check if pv exists")
        utils_lib.run_cmd(self,"sudo vgs",expect_kw="datavga",msg="check if vg exists")

        utils_lib.run_cmd(self,"sudo vgremove datavga",msg="remove vg group")
        utils_lib.run_cmd(self,"sudo pvremove {}".format(test_part),msg="remove pv")

    def test_storage_parted_s(self):
        """
        case_name:
            test_storage_parted_s
        case_file:
            os_tests.tests.test_storage.TestStorage.test_storage_parted_s
        component:
            kernel
        bugzilla_id:
            2024355
        is_customer_case:
            True
        testplan:
            N/A
        maintainer:
            xiliang@redhat.com
        description:
            Test creation of a large number of partitions on a gpt disk using 'parted -s'.
        key_steps:
            # parted -s $blockdev mklabel gpt mkpart primary 1Mib 6Mib mkpart primary 6Mib 11Mib mkpart primary 11Mib 16Mib mkpart primary 16Mib 21Mib mkpart primary 21Mib 26Mib mkpart primary 26Mib 31Mib mkpart primary 31Mib 36Mib mkpart primary 36Mib 41Mib mkpart primary 41Mib 46Mib mkpart primary 46Mib 51Mib mkpart primary 51Mib 56Mib mkpart primary 56Mib 61Mib mkpart primary 61Mib 66Mib mkpart primary 66Mib 71Mib mkpart primary 71Mib 76Mib mkpart primary 76Mib 81Mib mkpart primary 81Mib 86Mib mkpart primary 86Mib 91Mib mkpart primary 91Mib 96Mib mkpart primary 96Mib 101Mib
        expect_result:
            No error threw and create all partitions.
        debug_want:
            - output from dmesg or journal
            - test debug log
        """
        test_disk = self._get_test_disk()
        cmd = 'sudo wipefs -a {}'.format(test_disk)
        utils_lib.run_cmd(self, cmd, msg="try to wipe all fs from {}".format(test_disk))
        cmd = "sudo parted -s {} mklabel gpt mkpart primary 1Mib 6Mib mkpart primary 6Mib 11Mib mkpart primary 11Mib 16Mib mkpart primary 16Mib 21Mib mkpart primary 21Mib 26Mib mkpart primary 26Mib 31Mib mkpart primary 31Mib 36Mib mkpart primary 36Mib 41Mib mkpart primary 41Mib 46Mib mkpart primary 46Mib 51Mib mkpart primary 51Mib 56Mib mkpart primary 56Mib 61Mib mkpart primary 61Mib 66Mib mkpart primary 66Mib 71Mib mkpart primary 71Mib 76Mib mkpart primary 76Mib 81Mib mkpart primary 81Mib 86Mib mkpart primary 86Mib 91Mib mkpart primary 91Mib 96Mib mkpart primary 96Mib 101Mib".format(test_disk)
        utils_lib.run_cmd(self, cmd, expect_ret=0, msg='create 20 partitions on {}'.format(test_disk))
        cmd = "sudo parted -s {} print free".format(test_disk)
        utils_lib.run_cmd(self, cmd, expect_ret=0, expect_kw='106MB', msg="check partitions created")

    def _test_attach_detach_disk(self, attach_or_detach, device_bus, *device_info):
        '''
        attach/detach disk/cdrom
        '''
        self.log.info('device info including is cdrom or not, is empty or not, device size')
        if device_info[0]:
            cmd = 'lsblk -d --output TYPE | grep rom | wc -l'
        else:
            cmd = 'lsblk -d --output TYPE | grep disk | wc -l'
        origin_rom_num = utils_lib.run_cmd(self, cmd, expect_ret=0)
        if device_bus == 'ide' or device_bus == 'sata':
            self.vm.stop(wait="True")
        try:
            if attach_or_detach == 'attach':
                self.vm.attach_disk(device_bus, device_info[2], device_info[0], device_info[1], wait=True)
            else:
                disk_uuid = self.vm.get_disk_uuid(2)
                self.vm.detach_disk(device_bus, disk_uuid, wait=True)
        except NotImplementedError:
            self.skipTest('attch disk func is not implemented in {}'.format(self.vm.provider))
        except UnSupportedAction:
            self.skipTest('attch disk func is not supported in {}'.format(self.vm.provider))
        if device_bus == 'ide' or device_bus == 'sata':
            self.vm.start(wait="True")
        utils_lib.init_connection(self, timeout=180)
        total_rom_num = utils_lib.run_cmd(self, cmd, expect_ret=0)
        if attach_or_detach == 'attach':
            change_num = int(total_rom_num) - int(origin_rom_num)
        else:
            change_num = int(origin_rom_num) - int(total_rom_num)
        self.assertEqual(
            change_num, 1,
            "number of new added cdrom is incorrect. "
            "Expect: %s, real: %s" % (1, change_num)
        )

    def test_add_ide_empty_cdrom(self):
        """
        case_name:
            test_add_ide_empty_cdrom
        case_file:
            os_tests.tests.test_storage.TestStorage.test_add_ide_empty_cdrom
        component:
            storage
        maintainer:
            mingli@redhat.com
        description:
            Test attach empty ide cdrom.
        key_steps:
            # Attach empty ide cdrom
        expect_result:
            No error threw.
        debug_want:
            - output from dmesg or journal
        """
        if not self.vm:
            self.skipTest("Skip this test case as no vm inited")
        self._test_attach_detach_disk("attach", "ide", True, True, 0)

    def test_add_sata_clone_cdrom_from_img_service(self):
        """
        case_name:
            test_add_sata_clone_cdrom_from_img_service
        case_file:
            os_tests.tests.test_storage.TestStorage.test_add_sata_clone_cdrom_from_img_service
        component:
            storage
        maintainer:
            mingli@redhat.com
        description:
            Test attach sata cdrom clone from image service and then read the content in VM.
        key_steps:
            # Attach sata cdrom and then read it's content
        expect_result:
            No error threw and cdrom content right.
        debug_want:
            - output from dmesg or journal
        """
        if not self.vm:
            self.skipTest("Skip this test case as no vm inited")
        self._test_attach_detach_disk("attach", "sata", True, False, 0)
        new_add_device_name=utils_lib.run_cmd(self, 'blkid --label OEMDRV', expect_ret=0).split('\n')[0]
        cmd = "sudo mkdir /mnt/mnt_new_cdrom \n sudo mount {} /mnt/mnt_new_cdrom".format(new_add_device_name)
        utils_lib.run_cmd(self, cmd, expect_ret=0)
        read_new_device = utils_lib.run_cmd(self, "sudo ls /mnt/mnt_new_cdrom", expect_ret=0)
        self.assertIn(
                    "ks.cfg",
                    read_new_device,
                    msg="Read files from new added cdrom failed")

    def test_add_remove_multi_scsi(self):
        """
        case_name:
            test_add_remove_multi_scsi
        case_file:
            os_tests.tests.test_storage.TestStorage.test_add_remove_multi_scsi
        component:
            storage
        maintainer:
            mingli@redhat.com
        description:
            Test add and remove scsi disk of random size for 10 times in the VM.
        key_steps:
            # Attach/detach scsi disk with random size and check in 10 cycels
        expect_result:
            No error threw and size check right.
        debug_want:
            - output from dmesg or journal
        """
        if not self.vm:
            self.skipTest("Skip this test case as no vm inited")
        for i in range(10):
            random_dev_size = random.randint(1,10)
            self.log.info('test add remove scsi for {} time(s), and test size is {}'.format(i+1,random_dev_size))
            cmd = 'lsblk -d --output NAME|grep -v NAME'
            origin_lsblk_name_list = utils_lib.run_cmd(self, cmd, expect_ret=0).split('\n')
            self._test_attach_detach_disk("attach", "scsi", False, False, random_dev_size)
            new_lsblk_name_list = utils_lib.run_cmd(self, cmd, expect_ret=0).split('\n')
            new_dev = [x for x in new_lsblk_name_list if x not in origin_lsblk_name_list][0]
            cmd = 'sudo fdisk -s /dev/{}'.format(new_dev)
            new_dev_size = utils_lib.run_cmd(self, cmd, expect_ret=0).split('\n')[0]
            self.assertEqual(
                int(new_dev_size), random_dev_size*1024*1024,
                "Device size for new disk is not right"
                "Expect: %s, real: %s" % (random_dev_size*1024*1024, new_dev_size)
            )
            self._test_attach_detach_disk("detach", "scsi", False)

    def tearDown(self):
        if 'blktests' in self.id():
            utils_lib.check_log(self, "trace", log_cmd='dmesg -T', cursor=self.cursor)
        else:
            utils_lib.check_log(self, "error,warn,fail,trace", log_cmd='dmesg -T', cursor=self.cursor)

if __name__ == '__main__':
    unittest.main()