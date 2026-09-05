import { describe, expect, it } from "vitest";
import type { RoomSnapshot } from "../../hooks/useDashboard";
import { groupRoomsByBlock } from "./roomBlocks";

const snapshot=(name:string,room_id=`room_${name.toLowerCase()}`):RoomSnapshot=>({
  room:{room_id,name,capacity:40,building:"University Building",floor:2,camera_id:"cam_001",behavior_profile:"classroom"},
  occupancy:{camera_id:"cam_001",room_id,occupancy:0,raw_occupancy:0,capacity:40,occupancy_percentage:0,status:"online",updated_at:"2026-09-01T00:00:00Z"},
});

describe("room block grouping",()=>{
  it("orders C, B, A spatially and sorts room numbers naturally",()=>{
    const groups=groupRoomsByBlock([snapshot("2A07"),snapshot("2C05"),snapshot("2B08"),snapshot("2B01"),snapshot("2C03"),snapshot("2A03")]);
    expect(groups.map(group=>group.block)).toEqual(["C","B","A"]);
    expect(groups[0].rooms.map(item=>item.room.name)).toEqual(["2C03","2C05"]);
    expect(groups[1].rooms.map(item=>item.room.name)).toEqual(["2B01","2B08"]);
    expect(groups[2].rooms.map(item=>item.room.name)).toEqual(["2A03","2A07"]);
  });

  it("sorts a complete block by room number regardless of API order",()=>{
    const groups=groupRoomsByBlock([snapshot("4B08"),snapshot("4B03"),snapshot("4B01"),snapshot("4B07"),snapshot("4B02"),snapshot("4B06"),snapshot("4B04"),snapshot("4B05")]);
    expect(groups[1].rooms.map(item=>item.room.name)).toEqual(["4B01","4B02","4B03","4B04","4B05","4B06","4B07","4B08"]);
  });

  it("assigns named ground-floor spaces by their map columns",()=>{
    const groups=groupRoomsByBlock([snapshot("Canteen","room_canteen"),snapshot("Girls' Common Room","room_girls_common"),snapshot("T.T. Ground","room_tt_ground")]);
    expect(groups.map(group=>group.rooms.map(item=>item.room.room_id))).toEqual([["room_tt_ground"],["room_canteen"],["room_girls_common"]]);
  });
});
