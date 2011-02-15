#!/usr/bin/python

import os
import re
from subprocess import Popen,PIPE

def find_device(data, pciid):
    id = re.escape(pciid)
    m = re.search("^" + id + "\s(.*)$", data, re.MULTILINE)
    return m.group(1)

class Device:
    def __init__(self):
        self.sectorsize = ""
        self.sectors = ""
        self.rotational = ""
        self.sysdir = ""
        self.host = ""
        self.model = ""
        self.holders = []
        self.diskname = ""
        self.partitions = []
        self.removable = ""
        self.start = ""

    def populate_model(self):
        try:
            f = open(self.sysdir + "/device/model")
            self.model = f.read().rstrip()
            f.close()
        except IOError:
            # do nothing
            pass

    def populate_sectors(self):
        try:
            f = open(self.sysdir + "/size")
            self.sectors = f.read().rstrip()
            f.close()
        except IOError:
            self.sectors = 0

    def populate_sector_size(self):
        try:
            f = open(self.sysdir + "/queue/hw_sector_size")
            self.sectorsize = f.read().rstrip()
            f.close()
        except IOError:
            self.sectorsize = ""

    def populate_rotational(self):
        try:
            f = open(self.sysdir + "/queue/rotational")
            rotation = f.read().rstrip()
            f.close()
        except IOError:
            self.rotational = "Could not determine rotational"
            return
        if rotation == "1":
            self.rotational = "Spinning disk"
        else:
            self.rotational = "SSD"

    def populate_host(self, pcidata):
        m = re.match(".+/\d+:(\w+:\w+\.\w)/host\d+/\s*", self.sysdir)
        if m:
            pciid = m.group(1)
            self.host = find_device(pcidata, pciid)
        else:
            self.host = ""

    def populate_diskname(self):
        m = re.match(".*/(.+)$", self.sysdir)
        self.diskname = m.group(1)

    def populate_holders(self):
        for dir in os.listdir(self.sysdir + "/holders"):
            if re.search("^dm-.*", dir):
                try:
                    f = open(self.sysdir + "/holders/" + dir + "/dm/name")
                    name = f.read().rstrip()
                    f.close()
                    self.holders.append(name)
                except IOError:
                    self.holders.append(dir)
            else:
                self.holders.append(dir)

    def populate_start(self):
        try:
            f = open(self.sysdir + "/start")
            self.start = f.read().rstrip()
            f.close()
        except IOError:
            pass

    def populate_partitions(self):
        for dir in os.listdir(self.sysdir):
            m = re.search("(" + self.diskname + "\d+)", dir)
            if m:
                partname = m.group(1)
                part = Device()
                part.sysdir = self.sysdir + "/" + partname
                part.populate_part_info()
                self.partitions.append(part)

    def populate_part_info(self):
        """ Only call this if we are a partition """
        self.populate_diskname()
        self.populate_holders()
        self.populate_sectors()
        self.populate_start()

    def populate_removable(self):
        try:
            f = open(self.sysdir + "/removable")
            remove = f.read().rstrip()
            f.close()
            if remove == "1":
                self.removable = "Yes"
            else:
                self.removable = "No"
        except IOError:
            self.removable = "No"

    def populate_all(self, pcidata):
        self.populate_diskname()
        self.populate_holders()
        self.populate_partitions()
        self.populate_removable()
        self.populate_model()
        self.populate_sectors()
        self.populate_sector_size()
        self.populate_rotational()
        self.populate_host(pcidata)

p = Popen(["lspci"], stdout=PIPE)
err = p.wait()
if err:
    print "Error running lspci"
    sys.exit()
pcidata = p.stdout.read()

devices = []

for block in os.listdir("/sys/block"):
    path = os.readlink(os.path.join("/sys/block/", block))
    if re.search("virtual", path):
        continue
    d = Device()
    d.sysdir = os.path.join("/sys/block", path)
    d.populate_all(pcidata)
    devices.append(d)    

for d in devices:
    print d.diskname
    print "\tHost:" + d.host
    print "\tModel: " + d.model
    print "\tSector size: " + d.sectorsize
    print "\tSectors: " + d.sectors
    print "\tRemovable: " + d.removable
    print "\tDisk type: " + d.rotational
    if len(d.holders) > 0:
        print "\tHolders:"
        for h in d.holders:
            print "\t\t" + h
    if len(d.partitions) > 0:
        print "\tPartitions:"
        for p in d.partitions:
            print "\t\t" + p.diskname
            print "\t\t\tStart: " + p.start
            print "\t\t\tSectors: " + p.sectors
            if len(p.holders) > 0:
                print "\t\t\tHolders:"
                for h in p.holders:
                    print "\t\t\t\t" + h

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
